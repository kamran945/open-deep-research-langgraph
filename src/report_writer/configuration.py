import os
from enum import Enum
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from dataclasses import dataclass

from src.report_writer.utils import load_config


class WriterProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the chatbot."""

    config_yaml = load_config()

    report_structure: str = config_yaml["default_report_structure"]
    number_of_queries: int = config_yaml["number_of_queries"]
    max_search_depth: int = 2  # Maximum number of reflection + search iterations

    planner_provider: str = config_yaml["planner_provider"]
    planner_model: str = config_yaml["planner_model"]

    query_writer_provider: str = config_yaml["query_writer_provider"]
    query_writer_model: str = config_yaml["query_writer_model"]

    section_writer_provider: str = config_yaml["section_writer_provider"]
    section_writer_model: str = config_yaml["section_writer_model"]

    section_grader_provider: str = config_yaml["section_grader_provider"]
    section_grader_model: str = config_yaml["section_grader_model"]

    final_section_writer_provider: str = config_yaml["final_section_writer_provider"]
    final_section_writer_model: str = config_yaml["final_section_writer_model"]

    search_api: str = config_yaml["search_api"]

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
