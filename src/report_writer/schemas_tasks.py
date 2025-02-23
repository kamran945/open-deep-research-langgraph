from typing import Annotated, List, TypedDict, Literal
from pydantic import BaseModel, Field
import operator


class ReportPlanInput(TypedDict):
    topic: str  # Report topic
    feedback_on_report_plan: str  # Feedback on the report plan


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class Section(BaseModel):
    section_number: int = Field(
        description="The section number in the report, corresponding to its position within the document."
    )
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    content: str = Field(description="The content of the section.")


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class SectionState(TypedDict):
    section: Section  # Report section
    search_iterations: int  # Number of search iterations done
    search_queries: list[SearchQuery]  # List of search queries
    source_str: str  # String of formatted source content from web search
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API


class GenerateSectionQueriesInput(TypedDict):
    sections: Section
    search_iterations: int


class SectionWebSearchInput(TypedDict):
    section: Section
    search_queries: list[SearchQuery]  # List of search queries
    search_iterations: int


class WriteSectionInput(TypedDict):
    section: Section  # Report section
    source_str: str  # String of formatted source content from web search
    search_iterations: int


class SectionGraderOutput(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Does the section meet requirements ('pass') or need revision ('fail')?"
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of targeted search queries to address gaps.",
    )


class RouterGraderDecisonInput(TypedDict):
    feedback: SectionGraderOutput
    section: Section  # Report section
    search_iterations: int


class FinalSectionWriterInput(TypedDict):
    section: Section  # Report section
    completed_sections: str  # String of formatted source content from web search


class FinalReportInput(TypedDict):
    sections_without_web_research: Sections
    sections_with_web_research: Sections
