import streamlit as st
import os
from pathlib import Path
import sqlite3
import pandas as pd

from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.agents.agent_toolkits import SQLDatabaseToolkit

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

def create_friendly_response(query, sql_result):
    """
    Generate a more conversational and context-aware response
    
    Args:
        query (str): User's original query
        sql_result (str): Result from SQL query
    
    Returns:
        str: Friendly, informative response
    """
    # Greetings and basic interactions
    query_lower = query.lower()
    
    if any(greeting in query_lower for greeting in ['hi', 'hello', 'hey']):
        return "Hello there! I'm your friendly database assistant. What would you like to know?"
    
    # General response handling
    if 'most' in query_lower or 'highest' in query_lower or 'top' in query_lower:
        return f"I found an interesting insight: {sql_result}. Would you like more details?"
    
    # Fallback to direct SQL result
    return f"Here's what I found: {sql_result}. Is there anything specific you'd like to know about this?"

def preview_database_schema(engine):
    """
    Retrieve and display database schema information
    
    Args:
        engine (sqlalchemy.engine.base.Engine): SQLAlchemy engine
    
    Returns:
        dict: Dictionary of table schemas and sample data
    """
    # Get inspector
    inspector = inspect(engine)
    
    # Get table names
    tables = inspector.get_table_names()
    
    # Collect schema and sample data
    schema_info = {}
    for table in tables:
        # Get column information
        columns = inspector.get_columns(table)
        column_details = [
            f"{col['name']} ({col['type']})" 
            for col in columns
        ]
        
        # Get sample data
        try:
            with engine.connect() as connection:
                sample_data = pd.read_sql(f"SELECT * FROM {table} LIMIT 25", connection)
                schema_info[table] = {
                    'columns': column_details,
                    'sample_data': sample_data
                }
        except Exception as e:
            schema_info[table] = {
                'columns': column_details,
                'sample_data': f"Error retrieving sample data: {str(e)}"
            }
    
    return schema_info

def main():
    st.set_page_config(
        page_title="Database Query Assistant", 
        page_icon="📊", 
        layout="wide"
    )
    st.title("🔍 Database Query Companion")
    st.sidebar.title("Database Configuration")

    # Database and API Key Configuration
    db_path = Path(__file__).parent / "student.db"
    api_key = st.sidebar.text_input("GROQ API Key", type="password")

    if not api_key:
        st.info("Please enter your GROQ API Key to get started.")
        return

    # Database Connection
    try:
        # Create SQLAlchemy engine directly
        engine = create_engine(f"sqlite:///{db_path}")
        
        # Create SQLDatabase with the engine
        db = SQLDatabase(engine)

        # Database Schema Preview
        st.sidebar.header("Database Preview")
        if st.sidebar.button("Show Database Schema"):
            with st.sidebar.expander("Database Schema and Sample Data"):
                schema_info = preview_database_schema(engine)
                for table, details in schema_info.items():
                    st.write(f"### Table: {table}")
                    st.write("**Columns:**")
                    st.write(", ".join(details['columns']))
                    
                    st.write("**Sample Data:**")
                    if isinstance(details['sample_data'], pd.DataFrame):
                        st.dataframe(details['sample_data'])
                    else:
                        st.write(details['sample_data'])

        # LLM Configuration
        llm = ChatGroq(
            api_key=api_key, 
            model="Llama3-8b-8192", 
            streaming=True
        )

        # SQL Agent Setup
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            verbose=False,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )

        # Chat Session Initialization
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi there! I'm your database assistant. Click 'Show Database Schema' in the sidebar to explore the data, then ask me anything!"}
            ]

        # Display Chat History
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        # User Input Handling
        if user_query := st.chat_input("Ask a query about the database"):
            # Add user query to session
            st.session_state.messages.append({"role": "user", "content": user_query})
            st.chat_message("user").write(user_query)

            # Process Query
            with st.chat_message("assistant"):
                try:
                    # Run the agent to get SQL result
                    sql_result = agent.run(user_query)
                    
                    # Generate friendly response
                    friendly_response = create_friendly_response(user_query, sql_result)
                    
                    # Display and store response
                    st.write(friendly_response)
                    st.session_state.messages.append({"role": "assistant", "content": friendly_response})

                except Exception as e:
                    error_msg = f"Oops! I'm having trouble understanding that query. Error: {e}"
                    st.write(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

    except Exception as e:
        st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()