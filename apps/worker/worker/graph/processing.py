from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from worker.services.tasks import TaskService


class ProcessingState(TypedDict, total=False):
    job_id: str
    document_id: str
    owner_id: str
    task_type: str
    agent_run_id: str
    payload: dict[str, Any]
    result: dict[str, Any]


def build_graph(tasks: TaskService):
    def identifiers(state: ProcessingState) -> tuple[UUID, UUID, UUID, UUID | None]:
        job_id = UUID(state["job_id"])
        document_id = UUID(state["document_id"])
        owner_id = UUID(state["owner_id"])
        run_id = UUID(state["agent_run_id"]) if state.get("agent_run_id") else None
        return job_id, document_id, owner_id, run_id

    async def process_document(state: ProcessingState) -> ProcessingState:
        job_id, document_id, owner_id, _ = identifiers(state)
        result = await tasks.process_document(job_id, document_id, owner_id)
        return {**state, "result": result}

    async def answer_question(state: ProcessingState) -> ProcessingState:
        job_id, document_id, owner_id, run_id = identifiers(state)
        payload = state.get("payload", {})
        if run_id is None:
            raise ValueError("answer_question requiere agent_run_id")
        result = await tasks.answer_question(
            job_id, document_id, owner_id, run_id, payload["question"]
        )
        return {**state, "result": result}

    async def summarize_document(state: ProcessingState) -> ProcessingState:
        job_id, document_id, owner_id, run_id = identifiers(state)
        if run_id is None:
            raise ValueError("summarize_document requiere agent_run_id")
        result = await tasks.summarize(job_id, document_id, owner_id, run_id)
        return {**state, "result": result}

    async def extract_fields(state: ProcessingState) -> ProcessingState:
        job_id, document_id, owner_id, run_id = identifiers(state)
        if run_id is None:
            raise ValueError("extract_fields requiere agent_run_id")
        result = await tasks.extract_fields(
            job_id,
            document_id,
            owner_id,
            run_id,
            state.get("payload", {})["fields"],
        )
        return {**state, "result": result}

    def route(state: ProcessingState) -> str:
        task_type = state["task_type"]
        if task_type not in {
            "process_document",
            "answer_question",
            "summarize_document",
            "extract_fields",
        }:
            raise ValueError(f"Tipo de trabajo no admitido: {task_type}")
        return task_type

    graph = StateGraph(ProcessingState)
    graph.add_node("process_document", process_document)
    graph.add_node("answer_question", answer_question)
    graph.add_node("summarize_document", summarize_document)
    graph.add_node("extract_fields", extract_fields)
    graph.add_conditional_edges(
        START,
        route,
        {
            "process_document": "process_document",
            "answer_question": "answer_question",
            "summarize_document": "summarize_document",
            "extract_fields": "extract_fields",
        },
    )
    graph.add_edge("process_document", END)
    graph.add_edge("answer_question", END)
    graph.add_edge("summarize_document", END)
    graph.add_edge("extract_fields", END)
    return graph.compile()
