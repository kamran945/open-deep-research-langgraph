from langgraph.func import entrypoint
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import StreamWriter
from typing import List
import asyncio

from src.report_writer.tasks import (
    generate_report_plan,
    human_feedback,
    generate_section_queries,
    search_web,
    write_section,
    write_final_sections,
    compile_final_report,
)
from src.report_writer.configuration import Configuration

checkpointer = MemorySaver()


@entrypoint(checkpointer=checkpointer)
async def report_planner_workflow(
    input: dict, config: RunnableConfig, writer: StreamWriter, *, previous: dict
) -> dict:
    """Research report planner workflow"""
    print(f"\n{'='*50}\n report_planner_workflow \n{'='*50}\n")

    final_result = ""

    # Inputs
    topic = input["topic"]
    feedback_on_report_plan = input.get("feedback_on_report_plan", None)

    configurable = Configuration.from_runnable_config(config=config)

    while True:
        report_plan_input = {
            "topic": topic,
            "feedback_on_report_plan": feedback_on_report_plan,
        }
        writer("generate_report_plan started...")

        # get list of sections
        list_of_sections = await generate_report_plan(
            state=report_plan_input, config=config
        )
        writer("generate_report_plan finished...")

        feedback = await human_feedback(state=list_of_sections["sections"])

        if not feedback["generate_report_plan"]:
            futures = [
                generate_section_queries(
                    {
                        "section": section["section"],
                        "search_iterations": section["search_iterations"],
                    }
                )
                for section in feedback["sections_with_web_research"]
            ]

            results = await asyncio.gather(*futures)

            print("--------------------------------")
            print(f"section_queries:\n{results}")

            futures = [
                search_web(
                    {
                        "section": result["section"],
                        "search_queries": result["search_queries"],
                        "search_iterations": result["search_iterations"],
                    },
                    config=config,
                )
                for result in results
            ]
            web_results = await asyncio.gather(*futures)

            print("--------------------------------")
            print(f"len web results: {len(web_results)}")
            print("--------------------------------")
            print(f"web_results:\n{web_results}")

            sections_search_iterations = {
                "sections_without_web_research": feedback[
                    "sections_without_web_research"
                ],
                "sections_with_web_research": web_results,
            }
            return sections_search_iterations
        else:
            feedback_on_report_plan = feedback["feedback_on_report_plan"]
            continue


@entrypoint(checkpointer=checkpointer)
async def report_writer_workflow(
    input: dict, config: RunnableConfig, writer: StreamWriter, *, previous: dict
) -> dict:
    "Research report writer workflow"
    print(f"\n{'='*50}\n report_writer_workflow \n{'='*50}\n")

    final_result = ""

    # Inputs
    topic = input["topic"]
    feedback_on_report_plan = input.get("feedback_on_report_plan", None)

    configurable = Configuration.from_runnable_config(config=config)

    planner_output = await report_planner_workflow.ainvoke(
        {"topic": topic, "feedback_on_report_plan": feedback_on_report_plan}
    )

    sections_with_web_research = planner_output["sections_with_web_research"]
    sections_without_web_research = planner_output["sections_without_web_research"]

    futures = [
        write_section(
            state={
                "section": sections_with_web_research[i]["section"],
                "source_str": sections_with_web_research[i]["search_results"],
                "search_iterations": sections_with_web_research[i]["search_iterations"],
            },
            config=config,
        )
        for i in range(len(sections_with_web_research))
    ]
    completed_sections_with_web_research = await asyncio.gather(*futures)

    print("--------------------------------")
    print(f"section_grades:\n{completed_sections_with_web_research}")

    all_completed_sections_with_web_research = [
        completed_section["section"]
        for completed_section in completed_sections_with_web_research
    ]

    futures = [
        write_final_sections(
            state={
                "section": section["section"],
                "completed_sections": all_completed_sections_with_web_research,
            },
            config=config,
        )
        for section in sections_without_web_research
    ]
    final_sections_without_web_research = await asyncio.gather(*futures)

    print("--------------------------------")
    print(
        f"final_sections_without_web_research:\n{final_sections_without_web_research}"
    )

    final_report = compile_final_report(
        state={
            "sections_without_web_research": final_sections_without_web_research,
            "sections_with_web_research": completed_sections_with_web_research,
        }
    )

    return final_report
