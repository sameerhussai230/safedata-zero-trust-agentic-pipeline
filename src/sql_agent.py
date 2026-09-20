import os
import pandas as pd
from sqlalchemy import create_engine
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import config

def ask_sql_agent(query: str) -> str:
    db = SQLDatabase.from_uri(config.GOLD_DB_URI)
    llm = ChatGroq(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
    agent_executor = create_sql_agent(llm, db=db, agent_type="tool-calling", verbose=True)
    try:
        response = agent_executor.invoke({"input": query})
        return response.get("output", "I could not find an answer.")
    except Exception as e:
        return f"Error executing SQL: {str(e)}"

def generate_dynamic_questions(db_uri: str) -> list:
    """
    Dynamically analyzes the database schema and 1 sample row to ask the LLM 
    to generate highly relevant NLP-to-SQL questions specific to the dataset.
    """
    try:
        db = SQLDatabase.from_uri(db_uri)
        table_info = db.get_table_info()
        
        # Extract 1 sample row to give the LLM perfect context of the values
        engine = create_engine(db_uri)
        sample_row_df = pd.read_sql(f"SELECT * FROM {config.TABLE_NAME} LIMIT 1", engine)
        sample_row_dict = sample_row_df.to_dict(orient="records")[0] if not sample_row_df.empty else "No data available"
        
        llm = ChatGroq(model=config.LLM_MODEL, temperature=config.LLM_SUGGESTION_TEMP)
        prompt = PromptTemplate.from_template(
            "You are an expert data analyst. Here is the SQL schema for a newly uploaded dataset:\n"
            "{schema}\n\n"
            "Here is 1 sample row from this dataset:\n"
            "{sample_row}\n\n"
            "Make exactly 5 questions which user can ask by NLP to SQL system, like grouping, aggregation. "
            "Questions should focus on combining numeric metrics with categorical groupings (e.g., total sales by category, average balance by department). "
            "Return ONLY the 5 questions, one per line, with absolutely no numbers, bullet points, or extra text."
        )
        
        chain = prompt | llm
        response = chain.invoke({"schema": table_info, "sample_row": str(sample_row_dict)})
        
        # Clean up LangChain output
        raw_questions = response.content.strip().split("\n")
        cleaned_questions = [q.strip("- *1234567890. ") for q in raw_questions if q.strip()]
        
        if len(cleaned_questions) < 2:
            return ["What is the total sum of metrics grouped by category?", "Show me the top 5 records by highest amount."]
            
        return cleaned_questions[:5]
    
    except Exception as e:
        print(f"Error generating dynamic questions: {e}")
        return [
            "How many total rows are in this dataset?",
            "What are the distinct categories in this table?",
            "Can you provide a statistical summary of the numeric columns?"
        ]