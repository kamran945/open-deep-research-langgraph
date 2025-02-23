# Prompt to generate search queries to help with planning the report
report_planner_query_writer_instructions = """You are an expert technical writer assisting in report planning.  

<Report Topic>  
{topic}  
</Report Topic>  

<Report Structure>  
{report_structure}  
</Report Structure>  

<Task>  
Generate {number_of_queries} highly effective search query/queries to gather comprehensive information for structuring the report.  

Queries must:  
1. Align with the report topic.  
2. Fulfill the structural requirements outlined.  
3. Be precise enough to find high-quality, relevant sources while ensuring broad coverage.  
</Task>  
"""

# Prompt to generate the report plan
report_planner_instructions = """You are an expert report planner. Your task is to generate a structured outline for a report.  

<Instructions>  
- Create a list of report sections, each with:  
  - **Name**: Section title  
  - **Description**: Brief overview of key topics  
  - **Research**: Indicate if web research is needed  
  - **Content**: Leave blank for now  

- **Introduction & Conclusion** should not require research, as they summarize other sections.  
</Instructions>  

<Topic>  
{topic}  
</Topic>  

<Report Structure>  
Follow this Structure:  
{report_structure}  
</Report Structure>  

<Context>  
Use this context to guide the section planning:  
{context}  
</Context>  

<Feedback>  
Incorporate this feedback (if provided):  
{feedback}  
</Feedback>  
"""

# Query writer instructions
section_query_writer_instructions = """You are an expert technical writer generating precise web search queries to gather comprehensive information for a technical report section.

<Section Topic>
{section_topic}
</Section Topic>

<Task>
Generate {number_of_queries} search query/queries to collect in-depth information on the section topic. The queries must:
- Directly relate to the topic.
- Cover different key aspects of the topic.

Ensure the queries are specific enough to retrieve high-quality, relevant sources.
</Task>
"""
# Section writer instructions
section_writer_instructions = """You are an expert technical writer crafting a section of a technical report.

## Section Topic  
{section_topic}  

## Existing Content (if any)  
{section_content}  

## Source Material  
{context}  

## Writing Instructions  
- If no content exists, write from scratch.  
- If content exists, synthesize it with new information.  

## Style & Structure  
- **Strict 150-200 word limit**  
- **Start with a bold key insight**  
- Clear, technical language (no marketing)  
- Short paragraphs (2-3 sentences max)  
- Use ## for section title (Markdown)  
- **Use ONE structural element (if needed):**  
  - A focused table (Markdown syntax) comparing 2-3 key points  
  - OR a concise list (3-5 items) using proper Markdown syntax  

## Quality Checks  
- **Exact word count (excluding title & sources)**  
- One **specific** example or case study  
- No preamble before section content  
- Sources cited at the end in this format:  
  - `- Title: URL`
"""
# Instructions for section grading
section_grader_instructions = """Review a report section relative to the specified topic:

<section topic>
{section_topic}
</section topic>

<section content>
{section}
</section content>

<task>
Evaluate whether the section adequately covers the topic by checking technical accuracy and depth.

If the section fails any criteria, generate specific follow-up search queries to gather missing information.
</task>

<format>
    grade: Literal["pass","fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )
</format>
"""
final_section_writer_instructions = """You are an expert technical writer synthesizing information into a report section.

<Section topic>  
{section_topic}  
</Section topic>

<Available report content>  
{context}  
</Available report content>

<Task>  
1. **Section Guidelines:**  
   - **Introduction:**  
     - Use `#` for report title (Markdown).  
     - 50-100 words.  
     - Clearly state the report’s core motivation.  
     - No lists, tables, or sources.  

   - **Conclusion/Summary:**  
     - Use `##` for section title (Markdown).  
     - 100-150 words.  
     - **Comparative reports:** Must include a concise Markdown table summarizing key insights.  
     - **Non-comparative reports:** Use at most **one** structural element (table or short list).  
     - End with key takeaways or next steps.  
     - No sources section.  

2. **Writing Approach:**  
   - Use precise, impactful language.  
   - Prioritize key insights over generalities.  
   - Every word should add value.  

</Task>

<Quality Checks>  
- **Introduction:** 50-100 words, `#` title, no structural elements, no sources.  
- **Conclusion:** 100-150 words, `##` title, at most **one** structural element, no sources.  
- Use proper Markdown formatting.  
- No preamble, word count, or extra instructions in response.  
</Quality Checks>
"""
