from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig

from langgraph.func import task, entrypoint
from langgraph.constants import Send
from langgraph.types import interrupt, Command

from src.report_writer.schemas_tasks import (
    ReportPlanInput,
    Queries,
    Section,
    Sections,
    SectionState,
    GenerateSectionQueriesInput,
    SectionWebSearchInput,
    WriteSectionInput,
    SectionGraderOutput,
    FinalSectionWriterInput,
    FinalReportInput,
)
from src.report_writer.configuration import Configuration
from src.report_writer.prompts import (
    report_planner_query_writer_instructions,
    report_planner_instructions,
    section_query_writer_instructions,
    section_writer_instructions,
    section_grader_instructions,
    final_section_writer_instructions,
)
from src.report_writer.utils import (
    tavily_search_async,
    deduplicate_and_format_sources,
    duckduckgo_search_async,
    deduplicate_and_format_sources_duck,
    format_sections,
)


@task(name="generate_report_plan")
async def generate_report_plan(state: ReportPlanInput, config: RunnableConfig):
    """Generate the report plan"""
    print(f"\n{'='*50}\n generate_report_plan \n{'='*50}\n")

    # Inputs
    topic = state["topic"]
    feedback = state.get("feedback_on_report_plan", None)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    report_structure = configurable.report_structure
    number_of_queries = configurable.number_of_queries

    # Convert JSON object to string if necessary
    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    # Set writer model (model used for query writing and section writing)
    query_writer_provider = configurable.query_writer_provider
    query_writer_model_name = configurable.query_writer_model
    query_writer_model = init_chat_model(
        model=query_writer_model_name,
        model_provider=query_writer_provider,
        temperature=0,
    )
    query_writer_structured = query_writer_model.with_structured_output(Queries)

    # Format system instructions
    query_writer_system_instructions = report_planner_query_writer_instructions.format(
        topic=topic,
        report_structure=report_structure,
        number_of_queries=number_of_queries,
    )

    # Generate queries
    queries_object = query_writer_structured.invoke(
        [SystemMessage(content=query_writer_system_instructions)]
        + [
            HumanMessage(
                content="Generate search queries that will help with planning the sections of the report."
            )
        ]
    )

    # Web search
    query_list = [query.search_query for query in queries_object.queries]

    print("--------------------------------")
    print(f"query object in generate_plan {queries_object}")
    print("--------------------------------")
    print(f"query list in generate_plan {query_list}")

    # Get the search API
    search_api = configurable.search_api

    # Search the web
    if search_api == "tavily":
        web_search_results = await tavily_search_async(query_list)
        web_search_results_formatted = deduplicate_and_format_sources(
            web_search_results, max_tokens_per_source=600, include_raw_content=False
        )
    elif search_api == "duckduckgo":
        web_search_results = await duckduckgo_search_async(query_list)
        web_search_results_formatted = deduplicate_and_format_sources_duck(
            web_search_results
        )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    # Format system instructions
    system_instructions_sections = report_planner_instructions.format(
        topic=topic,
        report_structure=report_structure,
        context=web_search_results_formatted,
        feedback=feedback,
    )

    # Set the planner provider
    planner_provider = configurable.planner_provider

    # Set the planner model
    planner_model = configurable.planner_model

    # Set the planner model
    planner_llm = init_chat_model(model=planner_model, model_provider=planner_provider)

    # Generate sections
    planner_structured_llm = planner_llm.with_structured_output(Sections)
    report_sections = planner_structured_llm.invoke(
        [SystemMessage(content=system_instructions_sections)]
        + [
            HumanMessage(
                content="""Generate the sections of the report. Your response must include a 'sections' field containing a list of sections. 
                Each section must have: 'section_number', 'name', 'description', 'plan', 'research', and 'content' fields.
                Remember not to miss any fields mentioned above."""
            )
        ]
    )

    # Get sections
    sections = report_sections.sections

    return {"sections": sections}


@task(name="human_feedback")
async def human_feedback(state: Sections, config: RunnableConfig):
    """Get feedback on the report plan"""
    print(f"\n{'='*50}\n human_feedback \n{'='*50}\n")

    # Get sections
    sections = state
    sections_str = "\n\n".join(
        f"{section.section_number} - Section: {section.name}\n"
        f"Description: {section.description}\n"
        f"Research needed: {'Yes' if section.research else 'No'}\n"
        for section in sections
    )

    # Get feedback on the report plan from interrupt
    feedback = interrupt(
        f"Please provide feedback on the following report plan. \n\n{sections_str}\n\n Does the report plan meet your needs? Pass 'true' to approve the report plan or provide feedback to regenerate the report plan:"
    )

    # If the user approves the report plan, kick off section writing
    if isinstance(feedback, bool) and feedback is True:

        final_output = {}
        final_output["generate_report_plan"] = False
        final_output["feedback_on_report_plan"] = feedback
        final_output["sections_with_web_research"] = [
            {"section": s, "search_iterations": 0} for s in sections if s.research
        ]
        final_output["sections_without_web_research"] = [
            {"section": s, "search_iterations": 0} for s in sections if not s.research
        ]
        return final_output

    # If the user provides feedback, regenerate the report plan
    elif isinstance(feedback, str):

        final_output = {}
        final_output["generate_report_plan"] = True
        final_output["feedback_on_report_plan"] = feedback
        final_output["sections_with_web_research"] = [
            {"section": s, "search_iterations": 0} for s in sections if s.research
        ]
        final_output["sections_without_web_research"] = [
            {"section": s, "search_iterations": 0} for s in sections if not s.research
        ]
        return final_output
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")


@task
async def generate_section_queries(
    state: GenerateSectionQueriesInput, config: RunnableConfig
):
    """Generate search queries for a report section"""
    print(f"\n{'='*50}\n generate_section_queries \n{'='*50}\n")

    # Get state
    section = state["section"]
    search_iterations = state["search_iterations"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries

    # Generate queries
    query_writer_provider = configurable.query_writer_provider
    query_writer_model_name = configurable.query_writer_model
    query_writer_model = init_chat_model(
        model=query_writer_model_name,
        model_provider=query_writer_provider,
        temperature=0,
    )
    query_writer_structured = query_writer_model.with_structured_output(Queries)

    # Format system instructions
    section_query_writer_system_instructions = section_query_writer_instructions.format(
        section_topic=section.description, number_of_queries=number_of_queries
    )

    # Generate queries
    queries = query_writer_structured.invoke(
        [SystemMessage(content=section_query_writer_system_instructions)]
        + [HumanMessage(content="Generate search queries on the provided topic.")]
    )
    return {
        "section": section,
        "search_queries": queries.queries,
        "search_iterations": search_iterations,
    }


async def search_web(state: SectionWebSearchInput, config: RunnableConfig):
    """Search the web for each query, then return a list of raw sources and a formatted string of sources."""
    print(f"\n{'='*50}\n search_web \n{'='*50}\n")

    # Get state
    search_queries = state["search_queries"]
    section = state["section"]
    print("--------------------------------")
    print("search_queries")
    print(state)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Web search
    query_list = [query.search_query for query in search_queries]

    # Get the search API
    search_api = configurable.search_api

    print("--------------------------------")
    print("query_list")
    print(query_list)

    # Search the web
    if search_api == "tavily":
        web_search_results = await tavily_search_async(query_list)
        web_search_results_formatted = deduplicate_and_format_sources(
            web_search_results, max_tokens_per_source=600, include_raw_content=False
        )
    elif search_api == "duckduckgo":
        web_search_results = await duckduckgo_search_async(query_list)
        web_search_results_formatted = deduplicate_and_format_sources_duck(
            web_search_results
        )
    else:
        raise ValueError(f"Unsupported search API: {configurable.search_api}")

    return {
        "section": section,
        "section_queries": search_queries,
        "search_results": web_search_results_formatted,
        "search_iterations": state["search_iterations"] + 1,
    }


@task(name="write_section")
async def write_section(state: WriteSectionInput, config: RunnableConfig):
    """Write a section of the report"""
    print(f"\n{'='*50}\n write_section \n{'='*50}\n")

    # Get state
    section = state["section"]
    source_str = state["source_str"]
    search_queries = state.get("search_queris", "")
    search_iterations = state["search_iterations"]

    goto = None

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    while True:

        # Format system instructions
        section_writer_system_instructions = section_writer_instructions.format(
            section_title=section.name,
            section_topic=section.description,
            context=source_str,
            section_content=section.content,
        )

        # Generate section
        section_writer_provider = configurable.section_writer_provider
        section_writer_model_name = configurable.section_writer_model
        section_writer_model = init_chat_model(
            model=section_writer_model_name,
            model_provider=section_writer_provider,
            temperature=0,
        )
        section_content = section_writer_model.invoke(
            [SystemMessage(content=section_writer_system_instructions)]
            + [
                HumanMessage(
                    content="Generate a report section based on the provided sources."
                )
            ]
        )

        # Write content to the section object
        section.content = section_content.content

        # Grade prompt
        section_grader_instructions_formatted = section_grader_instructions.format(
            section_topic=section.description, section=section.content
        )
        print(f"\n{'-'*50}\n section_writer_grader_structured_llm \n{'-'*50}\n")

        # Feedback
        section_grader_provider = configurable.section_grader_provider
        section_grader_model_name = configurable.section_grader_model
        section_grader_llm = init_chat_model(
            model=section_grader_model_name,
            model_provider=section_grader_provider,
            temperature=0,
        )
        section_grader_structured_llm = section_grader_llm.with_structured_output(
            SectionGraderOutput
        )
        print("------------------------")
        print("feedback")
        feedback = section_grader_structured_llm.invoke(
            [SystemMessage(content=section_grader_instructions_formatted)]
            + [
                HumanMessage(
                    content="Grade the report and consider follow-up questions for missing information:"
                )
            ]
        )
        print("------------------------")
        print("TESTING WEB SEARCH FOR WRITING")
        print("------------------------")
        feedback.grade == "fail"
        if (
            feedback.grade == "pass"
            or state["search_iterations"] >= configurable.max_search_depth
        ):

            goto = "end"

            return {
                "section": section,
                "search_results": source_str,
                "search_iterations": search_iterations,
                "search_queries": search_queries,
                "goto": goto,
            }
        else:

            result = await search_web(
                state={
                    "section": section,
                    "search_queries": feedback.follow_up_queries,
                    "search_iterations": state["search_iterations"],
                },
                config=config,
            )
            # result = future.result()
            section = result["section"]
            source_str = result["search_results"]
            search_queries = result["section_queries"]
            search_iterations = result["search_iterations"]
            goto = "search_web"

        return {
            "section": section,
            "search_results": source_str,
            "search_iterations": search_iterations,
            "search_queries": search_queries,
            "goto": goto,
        }


@task(name="write_final_sections")
async def write_final_sections(state: FinalSectionWriterInput, config: RunnableConfig):
    """Write final sections of the report, which do not require web search and use the completed sections as context"""
    """Write a section of the report"""
    print(f"\n{'='*50}\n write_final_sections \n{'='*50}\n")
    print()
    print(state)
    print()

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get state
    section = state["section"]
    # completed_report_sections = state["report_sections_from_research"]
    completed_report_sections = format_sections(state["completed_sections"])

    print("----------------------------------------------------------------")
    print("completed_report_sections")
    print(completed_report_sections)
    print("----------------------------------------------------------------")

    # Format system instructions
    final_section_writer_system_instructions = final_section_writer_instructions.format(
        section_title=section.name,
        section_topic=section.description,
        context=completed_report_sections,
    )

    # Generate section
    final_writer_provider = configurable.final_section_writer_provider
    final_writer_model_name = configurable.final_section_writer_model
    final_writer_model = init_chat_model(
        model=final_writer_model_name,
        model_provider=final_writer_provider,
        temperature=0,
    )
    section_content = final_writer_model.invoke(
        [SystemMessage(content=final_section_writer_system_instructions)]
        + [
            HumanMessage(
                content="Generate a report section based on the provided sources."
            )
        ]
    )
    print("----------------------------------------------------------------")
    print("final sections")
    print(section_content.content)

    # Write content to section
    section.content = section_content.content

    # Write the updated section to completed sections
    return {
        "section": section,
    }


def compile_final_report(state: FinalReportInput):
    """Compile the final report"""

    # Get sections
    sections_without_web_research = state["sections_without_web_research"]
    sections_with_web_research = state["sections_with_web_research"]

    all_sections = sections_without_web_research + sections_with_web_research
    print("--------------------------------------------------------")
    print("all_sections")
    print(all_sections)

    # Sort by 'value' key
    sorted_sections_list = sorted(
        all_sections, key=lambda x: x["section"].section_number
    )

    # Compile final report
    final_report = "\n\n".join([s["section"].content for s in sorted_sections_list])

    print(f"{'='*50}\nFINAL REPORT\n{'='*50}\n\n{final_report}\n{'='*50}\n")

    return {"final_report": final_report}
