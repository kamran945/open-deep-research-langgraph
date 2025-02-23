# open-deep-research-langgraph
Automated Research Report Generation with LangGraph Functional API

# Automated Research Report Generation with LangGraph Functional API

## Overview

This repository implements an automated research report generation system using the **LangGraph Functional API**. It follows a structured workflow where different phases of report writing are handled asynchronously. This implementation is inspired by the [Open Deep Research](https://github.com/langchain-ai/open_deep_research/tree/main) repository but adapts it to **LangGraph's Functional API** rather than the Graph API.

## How It Works

### Plan and Execute
This workflow follows a **plan-and-execute** approach that separates planning from research. This allows for **human-in-the-loop approval** of a report plan before proceeding to the more time-consuming research phase.

- A **reasoning model** is used to **plan the report sections**.
- Web search is used during the planning phase to gather general information about the report topic.
- Users can **provide a predefined report structure** to guide the sections.
- Users can **give feedback on the report plan** before moving forward.

### Research and Write
Each report section is written **in parallel**, ensuring faster generation.

- The research assistant performs **asynchronous web searches** via **Tavily API** or **DuckDuckGo** (or Perplexity) to gather relevant information.
- It **reflects on each section** and **suggests follow-up questions** to deepen the research.
- This iterative research process continues for as many iterations as needed.
- **Final sections** like introductions and conclusions are written (also asynchronously) **after** the main body is completed for better coherence.

### Managing Different Report Types
This system is built on **LangGraph**, which provides **native configuration management**.  
The report structure is a configurable field, allowing users to create different assistants for different types of reports.

## Customizing the Report

You can fine-tune the research assistant’s behavior using the following parameters:

- **`report_structure`**: Define a custom structure for your report *(defaults to a standard research format)*.
- **`number_of_queries`**: Number of search queries to generate per section *(default: 2)*.
- **`max_search_depth`**: Maximum number of research iterations *(default: 2)*.
- **`planner_model`**: Specific model for planning *(`can be a reasoning model`)*.
- **`query_writer_model`**: Model for query writing.
- **`section_writer_model`**: Model for writing different sections that require websearch.
- **`section_grader_model`**: Model for grading the sections written by the `section_writer_model`.
- **`final_section_writer_model`**: Model for writing the sections of the report that do not require websearch.
- **`search_api`**: API to use for web searches *(Tavily or some other search api)*.

These configurations allow users to **adjust the research depth, choose different AI models, and customize the entire report generation process**. `config.yaml` file can be used for the configuration settings.

## Features of This Research Assistant

This research assistant follows a workflow similar to **OpenAI Deep Research** and **Gemini Deep Research** but allows full customization. You can:

- Provide an **outline** with a desired report structure.
- Set the **planner model** (e.g., **DeepSeek, OpenAI reasoning model**).
- Set other models writing queries, sections, grading etc (e.g., **Anthropic Claude, DeepSeek, OpenAI reasoning model**).
- Give **feedback on the plan of report sections** and iterate until user approval.
- Choose the **search API** (e.g., **Tavily, Perplexity, DuckDuckgo**) and set the **number of searches** per research iteration.
- Define **search depth** for each section (number of **iterations of writing, reflection, search, and re-writing**).
- Customize the **writer model** (e.g., **Anthropic Claude**).

## Workflow Diagram

Below is the workflow diagram illustrating how the system operates:

![Workflow Diagram](path_to_your_image.png)

---

This implementation optimizes **research efficiency, parallel execution, and customization**, making it a powerful tool for automated research and report generation.

## Original Implementation: Graph API Approach

In the original implementation, the process was structured using LangGraph's Graph API. This approach involved:

- **Defining Nodes**: Each task, such as data collection, analysis, and drafting, was represented as a node in the graph.
- **Establishing Edges**: Dependencies between tasks were defined through directed edges, outlining the sequence and flow of operations.
- **State Management**: A centralized state was maintained, with reducers managing updates as data flowed through the graph.
- **Visualization**: The graph structure provided a clear visual representation of the workflow, aiding in debugging and optimization.

While effective, this method required meticulous planning of the graph structure and explicit state management.

## Current Implementation: Functional API Approach

Transitioning to the Functional API, the workflow is now defined using Python's native control flow constructs, enhancing readability and maintainability. Key aspects include:

- **Entrypoint Definition**: The `@entrypoint` decorator designates the main function, managing the overall workflow execution.
- **Task Creation**: Individual tasks are encapsulated using the `@task` decorator, allowing for asynchronous execution and easy integration of models for specific tasks.
- **Control Flow**: Utilizing standard Python constructs (`if` statements, loops), the workflow dynamically manages task execution based on real-time data and conditions.
- **State Persistence**: Built-in support for checkpointing ensures that intermediate results are saved, enabling the workflow to resume seamlessly after interruptions.

### Report Generation Process

The report generation process encompasses several asynchronous tasks:

1. **Asynchronous Web Search**: Gathering relevant information from various online sources concurrently to expedite data collection.
2. **Asynchronous Section Writing**: Drafting different sections of the report in parallel, each focusing on distinct aspects of the research topic.
3. **Human-in-the-Loop Review**: Incorporating a stage where human feedback is solicited to refine and validate the initial layout plan.
4. **Final Compilation**: Aggregating all sections into a cohesive report, ensuring consistency and coherence.

This modular approach allows for efficient handling of complex workflows, with each component operating independently yet cohesively within the overall process.

## Comparison: Graph API vs. Functional API

For a more detailed comparison, refer to the [Functional API vs. Graph API documentation](https://langchain-ai.github.io/langgraph/concepts/functional_api/#functional-api-vs-graph-api).

## Conclusion

By adopting LangGraph's Functional API, this project streamlines the process of automated research report generation. The approach offers enhanced flexibility, and improved maintainability, making it a robust solution for dynamic content creation workflows.

## How to use:
-   Clone this repository `git clone <repository-url>`
-   Initialize poetry with `poetry init -n`
-   Run `poetry config virtualenvs.in-project true` so that virtualenv will be present in project directory
-   Run `poetry env use <C:\Users\username\AppData\Local\Programs\Python\Python311\python.exe>` to create virtualenv in project (change username to your username)
-   Run `poetry shell`
-   Run `poetry install` to install requried packages
-   Create `.env` file and insert all keys: see `.env.example` file
-   Use test_generate_report_plan.ipynb notebook to test open-deep-research.
-   You can also use LangGraph Studio to test this Open Deep Research workflow. Follow the setup guidelines provided [here](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/#features) to get started.