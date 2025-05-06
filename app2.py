import streamlit as st
import os
from pathlib import Path
import sqlite3
import pandas as pd
import io
import base64
import time
import matplotlib.pyplot as plt
import seaborn as sns

from dotenv import load_dotenv
from euriai import EuriaiClient

# Load environment variables
load_dotenv()

# Initialize EuriAI client with your API key - no need for user input
euriai_client = EuriaiClient(
    api_key="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",  # Your API key
    model="gpt-4.1-nano"
)

def ask_euriai(prompt, max_tokens=600):
    """
    Ask EuriAI to generate a response with improved prompts
    """
    enhanced_prompt = f"""{prompt}

Important instructions:
1. Provide a complete, well-structured response with no cut-off sentences.
2. Keep your response concise and within {max_tokens} tokens.
3. Format your response with proper headings, bullet points, and paragraphs.
4. Use asterisks for emphasis on important points (*important*).
5. Use numbered lists for sequential steps or prioritized items.
6. Break content into clear sections with double line breaks between sections.
7. Structure content to be easily scannable with clear organization.
8. Do not ask any follow-up questions at the end of your response."""
    
    response = euriai_client.generate_completion(prompt=enhanced_prompt, temperature=0.5, max_tokens=max_tokens)
    if isinstance(response, dict) and 'choices' in response:
        return response['choices'][0]['message']['content']
    return response

def create_friendly_response(query, sql_result):
    """
    Generate a more conversational and context-aware response using EuriAI
    """
    prompt = f"""
    As a database assistant, create a friendly, conversational response to the user's query.
    
    User Query: "{query}"
    
    SQL Result: "{sql_result}"
    
    Your response should:
    1. Be conversational and helpful
    2. Highlight key insights from the data
    3. Provide context to the numbers where relevant
    4. Suggest follow-up questions if appropriate
    5. Be concise (max 3-4 sentences)
    """
    
    try:
        return ask_euriai(prompt, max_tokens=300)
    except Exception as e:
        # Fallback to a simpler method if EuriAI fails
        if 'most' in query.lower() or 'highest' in query.lower() or 'top' in query.lower():
            return f"I found an interesting insight: {sql_result}. Would you like more details?"
        else:
            return f"Here's what I found: {sql_result}. Is there anything specific you'd like to know about this?"

def generate_sql_explanation(query, sql_query):
    """
    Generate a user-friendly explanation of the SQL query
    """
    prompt = f"""
    Explain this SQL query in simple terms that a non-technical person would understand.
    
    User Query: "{query}"
    SQL Query: "{sql_query}"
    
    Your explanation should:
    1. Avoid technical jargon
    2. Be concise (2-3 sentences)
    3. Focus on what the query is trying to achieve
    """
    
    try:
        return ask_euriai(prompt, max_tokens=200)
    except Exception as e:
        # Fallback to a simpler method if EuriAI fails
        return f"This query is looking for information about {query.lower().replace('what', '').replace('how', '').replace('?', '')}."

def generate_data_insights(df, query):
    """
    Generate insights about the data
    """
    # Get dataframe info as text
    data_sample = df.head(5).to_string()
    
    prompt = f"""
    Analyze this dataset and provide 3 key insights that would be valuable to someone querying:
    "{query}"
    
    Data sample:
    {data_sample}
    
    Your insights should:
    1. Be specific to the data and query
    2. Highlight patterns, outliers, or interesting findings
    3. Be data-driven and objective
    4. Each insight should be 1-2 sentences only
    """
    
    try:
        return ask_euriai(prompt, max_tokens=350)
    except Exception as e:
        # Fallback to a simpler method if EuriAI fails
        return "The data shows interesting patterns that may answer your query. Take a look at the results to draw your own insights."

def preview_database_schema(connection):
    """
    Retrieve and display database schema information correctly
    """
    # Define a SQL query to get table info from SQLite
    tables_query = """
    SELECT name FROM sqlite_master WHERE type='table';
    """
    tables_df = pd.read_sql(tables_query, connection)
    
    # Collect schema and sample data
    schema_info = {}
    for table_name in tables_df['name']:
        # Skip internal SQLite tables
        if table_name.startswith('sqlite_'):
            continue
            
        # Get column information using a SQL query instead of SQLAlchemy inspector
        columns_query = f"PRAGMA table_info({table_name});"
        columns_df = pd.read_sql(columns_query, connection)
        
        column_details = [
            f"{row['name']} ({row['type']})" 
            for _, row in columns_df.iterrows()
        ]
        
        # Get row count using SQL COUNT
        count_query = f"SELECT COUNT(*) as count FROM {table_name};"
        count_df = pd.read_sql(count_query, connection)
        row_count = count_df['count'][0]
        
        # Get sample data
        try:
            sample_query = f"SELECT * FROM {table_name} LIMIT 25;"
            sample_data = pd.read_sql(sample_query, connection)
            
            schema_info[table_name] = {
                'columns': column_details,
                'sample_data': sample_data,
                'row_count': row_count
            }
        except Exception as e:
            schema_info[table_name] = {
                'columns': column_details,
                'sample_data': f"Error retrieving sample data: {str(e)}",
                'row_count': row_count
            }
    
    return schema_info

def create_visualization(df, query):
    """
    Create a simple visualization based on the dataframe
    """
    try:
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Set style
        sns.set_style("whitegrid")
        
        # Simple heuristics for chart type
        num_columns = df.select_dtypes(include=['number']).columns
        cat_columns = df.select_dtypes(include=['object']).columns
        
        if len(num_columns) >= 1 and len(cat_columns) >= 1:
            # Bar chart for categorical vs numeric
            if len(df) <= 15:  # Limit to prevent overcrowding
                sns.barplot(x=cat_columns[0], y=num_columns[0], data=df, ax=ax)
                plt.xticks(rotation=45)
            else:
                # Group by categorical and take mean of numeric
                grouped = df.groupby(cat_columns[0])[num_columns[0]].mean().reset_index()
                sns.barplot(x=cat_columns[0], y=num_columns[0], data=grouped, ax=ax)
                plt.xticks(rotation=45)
        elif len(num_columns) >= 2:
            # Scatter plot for numeric vs numeric
            sns.scatterplot(x=num_columns[0], y=num_columns[1], data=df, ax=ax)
        elif len(num_columns) == 1 and len(df) <= 50:
            # Histogram for single numeric column
            sns.histplot(df[num_columns[0]], kde=True, ax=ax)
        else:
            # Fallback to count plot for single categorical
            if len(cat_columns) >= 1 and len(df[cat_columns[0]].unique()) <= 15:
                sns.countplot(y=cat_columns[0], data=df, ax=ax, order=df[cat_columns[0]].value_counts().index)
            else:
                # Text-only plot as fallback
                ax.text(0.5, 0.5, "Data visualization not available for this query", 
                       horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
                ax.axis('off')
        
        # Set title based on query
        plt.title(f"Visualization for: {query[:50]}{'...' if len(query) > 50 else ''}", fontsize=14)
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        return buf
    except Exception as e:
        # Create an error message visualization
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Could not create visualization: {str(e)}", 
               horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        return buf

def execute_sql_query(connection, query):
    """
    Execute an SQL query directly and return results
    """
    try:
        # Try to execute as a SELECT query and return a dataframe
        df = pd.read_sql(query, connection)
        return {
            "success": True,
            "type": "dataframe",
            "result": df,
            "message": f"Query returned {len(df)} rows."
        }
    except pd.io.sql.DatabaseError:
        # If it's not a SELECT query, execute it differently
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            if cursor.rowcount >= 0:
                return {
                    "success": True,
                    "type": "update",
                    "result": None,
                    "message": f"Query executed successfully. {cursor.rowcount} rows affected."
                }
        except Exception as e:
            return {
                "success": False,
                "type": "error",
                "result": None,
                "message": f"Error executing query: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "type": "error",
            "result": None,
            "message": f"Error: {str(e)}"
        }

def generate_query_from_nl(natural_language_query):
    """
    Generate SQL query from natural language using EuriAI
    """
    # First, get the database schema to help the model
    try:
        # Database path
        db_path = Path(__file__).parent / "student.db"
        
        # Create direct connection for schema inspection
        connection = sqlite3.connect(db_path)
        
        # Get schema information
        schema_info = preview_database_schema(connection)
        
        # Format the schema info
        schema_text = ""
        for table_name, details in schema_info.items():
            schema_text += f"Table: {table_name} (Rows: {details['row_count']})\n"
            schema_text += "Columns: \n"
            for col in details['columns']:
                schema_text += f"  - {col}\n"
            schema_text += "\n"
        
        # Create the prompt
        prompt = f"""
        You are an expert SQL developer. Given the following database schema and a natural language query,
        write an SQLite SQL query that would answer the user's question.
        
        Database Schema:
        {schema_text}
        
        User's Natural Language Query: "{natural_language_query}"
        
        Respond ONLY with the SQL query, nothing else. Do not include backticks, explanation, or any other text.
        The query should be valid SQLite syntax.
        """
        
        # Use EuriAI to generate the SQL query
        sql_query = ask_euriai(prompt, max_tokens=250)
        
        # Clean up any potential formatting issues
        sql_query = sql_query.strip().replace('```sql', '').replace('```', '').strip()
        
        connection.close()
        
        return sql_query
        
    except Exception as e:
        return f"Error generating SQL: {str(e)}"

def main():
    st.set_page_config(
        page_title="Database Query Assistant", 
        page_icon="📊", 
        layout="wide"
    )
    
    # Custom CSS for better UI
    st.markdown("""
    <style>
    /* Main theme colors and fonts */
    :root {
        --primary-color: #5C67DE;
        --secondary-color: #31304D;
        --accent-color: #F4CE14;
        --light-bg: #F9F9F9;
        --dark-bg: #1E293B;
        --text-light: #F8FAFC;
        --text-dark: #1E293B;
        --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Global styles */
    .main {
        background-color: var(--light-bg);
        color: var(--text-dark);
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        color: var(--secondary-color);
        font-weight: 700 !important;
    }
    
    /* Header styling */
    .header-container {
        background-color: var(--primary-color);
        padding: 2rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .header-container h1 {
        color: white !important;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem;
    }
    
    .header-subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
        margin-bottom: 1.5rem;
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--card-shadow);
        border-left: 5px solid var(--primary-color);
    }
    
    .card-title {
        color: var(--primary-color);
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    
    .card-content {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Chat styling */
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
    }
    
    .user-message {
        background-color: #F1F5F9;
        border-left: 5px solid var(--secondary-color);
    }
    
    .assistant-message {
        background-color: #EFF6FF;
        border-left: 5px solid var(--primary-color);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Button styling */
    .stButton > button, .download-btn {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s;
        width: 100%;
        margin-top: 1rem;
    }
    
    .stButton > button:hover, .download-btn:hover {
        background-color: #4A52B3;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 4px 4px 0 0;
        padding: 10px 16px;
        height: auto;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    
    /* Chat input styling */
    .stTextInput > div > div > input {
        background-color: white;
        border-radius: 50px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="header-container">
        <h1>Database Query Assistant</h1>
        <div class="header-subtitle">Ask questions naturally • Get visual insights • Understand your data</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.title("Database Explorer")
    
    # Database Connection
    try:
        # Database path
        db_path = Path(__file__).parent / "student.db"
        
        # Create direct connection for schema inspection
        sqlite_connection = sqlite3.connect(db_path)
        
        # Database Schema Preview section
        with st.sidebar.expander("📚 Database Schema", expanded=False):
            # Use the direct connection method that we fixed
            schema_info = preview_database_schema(sqlite_connection)
            
            for table_name, details in schema_info.items():
                st.write(f"### {table_name}")
                st.write(f"**Rows:** {details['row_count']}")
                
                # Display columns in a nicer format
                col_df = pd.DataFrame({
                    'Column': [col.split(' ')[0] for col in details['columns']],
                    'Type': [col.split(' ')[1].strip('()') for col in details['columns']]
                })
                st.dataframe(col_df, hide_index=True)
                
                # Show sample data button
                if st.button(f"Show Sample Data: {table_name}"):
                    if isinstance(details['sample_data'], pd.DataFrame):
                        st.dataframe(details['sample_data'])
                    else:
                        st.write(details['sample_data'])
        
        # Example queries section
        with st.sidebar.expander("🔆 Example Queries", expanded=False):
            examples = [
                "Show me the top 5 students with the highest marks",
                "What is the average age of students in each class?",
                "How many students are in each section of Data Science?",
                "Which student has the lowest marks in DevOps?",
                "Compare the average marks between different classes"
            ]
            
            for example in examples:
                if st.button(example):
                    # Set as current query and run
                    st.session_state.current_query = example
                    # Rerun to process the new query
                    st.rerun()
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi there! I'm your database assistant. Click 'Show Database Schema' in the sidebar to explore the data, then ask me anything!"}
            ]
        if "current_query" not in st.session_state:
            st.session_state.current_query = ""
        if "current_result" not in st.session_state:
            st.session_state.current_result = None
        if "current_dataframe" not in st.session_state:
            st.session_state.current_dataframe = None
        if "sql_explanation" not in st.session_state:
            st.session_state.sql_explanation = None
        if "insights" not in st.session_state:
            st.session_state.insights = None
        if "chart_buffer" not in st.session_state:
            st.session_state.chart_buffer = None
        if "sql_query" not in st.session_state:
            st.session_state.sql_query = None
        
        # Main content layout
        chat_col, results_col = st.columns([1, 1])
        
        # Chat interface
        with chat_col:
            st.markdown("<h2>Chat with your Database</h2>", unsafe_allow_html=True)
            
            # Display chat history with custom styling
            for i, msg in enumerate(st.session_state.messages):
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message user-message">
                        <strong>You:</strong> {msg["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-message assistant-message">
                        <strong>Assistant:</strong> {msg["content"]}
                    </div>
                    """, unsafe_allow_html=True)
            
            # User input
            user_query = st.chat_input("Ask something about the database...", key="chat_input")
            
            # Check if example query was selected or user entered a query
            if st.session_state.current_query and not user_query:
                user_query = st.session_state.current_query
                st.session_state.current_query = ""  # Reset to avoid loops
            
            if user_query:
                # Add user query to session
                st.session_state.messages.append({"role": "user", "content": user_query})
                
                # Display user query
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {user_query}
                </div>
                """, unsafe_allow_html=True)
                
                # Process Query
                with st.spinner("Analyzing your query..."):
                    try:
                        # Show loading 
                        st.markdown("""
                        <div style="display: flex; justify-content: center; margin: 20px 0;">
                            <div style="border: 4px solid #f3f3f3; border-top: 4px solid #5C67DE; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
                        </div>
                        <style>
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        # Generate SQL query from natural language using EuriAI
                        sql_query = generate_query_from_nl(user_query)
                        st.session_state.sql_query = sql_query
                        
                        # Execute the generated SQL query
                        query_result = execute_sql_query(sqlite_connection, sql_query)
                        
                        if query_result["success"]:
                            if query_result["type"] == "dataframe":
                                # Store the dataframe result
                                st.session_state.current_dataframe = query_result["result"]
                                
                                # Convert dataframe to string for display
                                result_str = f"Query returned {len(query_result['result'])} rows."
                                
                                # Add a preview of the data
                                if len(query_result["result"]) > 0:
                                    result_head = query_result["result"].head(3).to_string()
                                    result_str += f"\n\nPreview:\n{result_head}"
                                    
                                    # Only show first 100 chars to avoid overwhelming
                                    if len(result_str) > 300:
                                        result_str = result_str[:300] + "..."
                            else:
                                # For non-SELECT queries
                                result_str = query_result["message"]
                                st.session_state.current_dataframe = None
                        else:
                            # Handle errors
                            result_str = query_result["message"]
                            st.session_state.current_dataframe = None
                            
                        st.session_state.current_result = result_str
                        
                        # Generate a friendly response using EuriAI
                        friendly_response = create_friendly_response(user_query, result_str)
                        
                        # Generate SQL explanation
                        if sql_query:
                            st.session_state.sql_explanation = generate_sql_explanation(user_query, sql_query)
                        else:
                            st.session_state.sql_explanation = "I processed your query using natural language understanding."
                        
                        # Generate insights if we have a dataframe
                        if st.session_state.current_dataframe is not None:
                            st.session_state.insights = generate_data_insights(
                                st.session_state.current_dataframe, 
                                user_query
                            )
                            
                            # Create visualization
                            st.session_state.chart_buffer = create_visualization(
                                st.session_state.current_dataframe,
                                user_query
                            )
                        
                        # Display and store response
                        st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <strong>Assistant:</strong> {friendly_response}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.session_state.messages.append({"role": "assistant", "content": friendly_response})
                        
                        # Auto-refresh to show results in the right panel
                        st.rerun()

                    except Exception as e:
                        error_msg = f"Oops! I'm having trouble understanding that query. Error: {e}"
                        st.markdown(f"""
                        <div class="chat-message assistant-message">
                            <strong>Assistant:</strong> {error_msg}
                        </div>
                        """, unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # Results area
        with results_col:
            if st.session_state.current_result:
                st.markdown("<h2>Query Results & Insights</h2>", unsafe_allow_html=True)
                
                # Tabs for different result views
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Results", "📝 SQL", "📈 Visualization", "🔍 Insights"])
                
                with tab1:
                    # Display results
                    if st.session_state.current_dataframe is not None:
                        st.dataframe(st.session_state.current_dataframe, use_container_width=True)
                    else:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                                Results
                            </div>
                            <div class="card-content">
                                {st.session_state.current_result}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with tab2:
                    # Display SQL query and explanation
                    if st.session_state.sql_query:
                        st.code(st.session_state.sql_query, language="sql")
                    
                    if st.session_state.sql_explanation:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                                Query Explanation
                            </div>
                            <div class="card-content">
                                {st.session_state.sql_explanation}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with tab3:
                    # Display visualization if available
                    if st.session_state.chart_buffer:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                                Data Visualization
                            </div>
                            <div class="card-content">
                                A visual representation of your query results.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.image(st.session_state.chart_buffer, use_column_width=True)
                    else:
                        st.info("No visualization available for this query.")
                
                with tab4:
                    # Display insights if available
                    if st.session_state.insights:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                                Key Insights
                            </div>
                            <div class="card-content">
                                {st.session_state.insights}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("No insights available for this query.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        
    # Close the SQLite connection when done
    try:
        sqlite_connection.close()
    except:
        pass

if __name__ == "__main__":
    main()