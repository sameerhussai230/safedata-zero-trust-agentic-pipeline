import streamlit as st
import os
import shutil
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import config
from src.masking_agent import mask_data_with_groq
from src.sql_agent import ask_sql_agent, generate_dynamic_questions
import generate_datasets  # Imported for auto-generation on cloud restart

load_dotenv()

st.set_page_config(page_title="SecureData Agentic BI", page_icon="🛡️", layout="wide")

# --- Custom CSS for UI Enhancements ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 400px !important; max-width: 500px !important; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] .stMarkdown li { font-size: 1.25rem !important; }
        [data-testid="stSidebar"] h2 { font-size: 2.2rem !important; }
        [data-testid="stSidebar"] label p { font-size: 1.25rem !important; }
        [data-testid="stSidebar"] [data-testid="stAlert"] div div p { font-size: 1.2rem !important; }
        [data-testid="stDataFrame"] { margin-top: 10px !important; margin-bottom: 20px !important; }
        @media print {
            [data-testid="stDataFrame"] { position: static !important; margin-top: 20px !important; page-break-inside: avoid !important; }
            .print-safe-alert { display: block !important; position: static !important; margin-bottom: 25px !important; break-inside: avoid; }
        }
    </style>
""", unsafe_allow_html=True)

# --- Boot Initialization (For Streamlit Cloud Ephemeral Storage) ---
# If the cloud server goes to sleep, it wipes local DBs. This auto-recreates them.
os.makedirs('data', exist_ok=True)
if not os.path.exists("data/bronze_ecommerce.db"):
    with st.spinner("Initializing simulated environments for first boot..."):
        generate_datasets.generate_all()

# --- Main Title & Description ---
st.title("🛡️ SecureData Agentic Zero-Trust Pipeline")
st.markdown("**A highly secure AI data pipeline that intelligently detects and masks PII during ETL, completely isolating sensitive data from LLMs while enabling business users to execute Natural Language to SQL analytics.**")

# --- UI State Management ---
if "gold_ready" not in st.session_state:
    st.session_state.gold_ready = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_dataset" not in st.session_state:
    st.session_state.current_dataset = None
if "dynamic_questions" not in st.session_state:
    st.session_state.dynamic_questions = []

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("🗄️ Select Dataset Schema")
    st.info("Choose a simulated environment or upload your own data.")
    
    dataset_choice = st.selectbox(
        "Available Datasets:", 
        ("E-Commerce (Retail)", "Healthcare (Medical Billing)", "Banking (Financial)", "Custom Upload (CSV/Excel)")
    )
    
    # Reset states if user changes dataset
    if dataset_choice != st.session_state.current_dataset:
        st.session_state.current_dataset = dataset_choice
        st.session_state.gold_ready = False
        st.session_state.messages = [] 
        st.session_state.dynamic_questions = []
        
    selected_db_path = None

    if dataset_choice == "Custom Upload (CSV/Excel)":
        st.markdown("### 📤 Upload Custom Data")
        st.caption(f"**Limits:** Max {config.MAX_ROWS_UPLOAD} rows for demo batching limits.")
        uploaded_file = st.file_uploader("Upload your file here", type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_custom = pd.read_csv(uploaded_file)
                else:
                    df_custom = pd.read_excel(uploaded_file)
                
                df_custom = df_custom.loc[:, ~df_custom.columns.str.contains('^Unnamed')]
                
                if df_custom.empty:
                    st.error("Uploaded file is empty. Please upload a valid file.")
                    st.stop()
                
                if len(df_custom) > config.MAX_ROWS_UPLOAD:
                    st.warning(f"File contains {len(df_custom)} rows. Truncating to first {config.MAX_ROWS_UPLOAD} rows.")
                    df_custom = df_custom.head(config.MAX_ROWS_UPLOAD)
                
                custom_db_path = "data/bronze_custom.db"
                engine_custom = create_engine(f"sqlite:///{custom_db_path}")
                df_custom.to_sql(config.TABLE_NAME, engine_custom, if_exists="replace", index=False)
                engine_custom.dispose()
                
                selected_db_path = custom_db_path
                st.success("File processed successfully!")
                
            except Exception as e:
                st.error(f"Error processing file: {e}")
                st.stop()
        else:
            st.info("Awaiting file upload...")
            st.stop()
            
    else:
        db_mapping = {
            "E-Commerce (Retail)": "data/bronze_ecommerce.db",
            "Healthcare (Medical Billing)": "data/bronze_healthcare.db",
            "Banking (Financial)": "data/bronze_banking.db"
        }
        selected_db_path = db_mapping[dataset_choice]

    st.divider()

    # BYOK Section moved Below Data Selection
    st.header("🔑 Configuration (BYOK)")
    st.info("If the default demo API key hits its daily limit, enter your own Groq API key here to continue.")
    user_api_key = st.text_input("Bring Your Own Key (Optional)", type="password", placeholder="gsk_...")
    st.markdown("[🔗 Get your free Groq API Key here](https://console.groq.com/keys)")
    
    # Safe fetch for Streamlit Cloud Secrets vs Local .env
    default_key = ""
    try:
        default_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
    except Exception:
        default_key = os.getenv("GROQ_API_KEY", "")
        
    active_key = user_api_key.strip() if user_api_key.strip() else default_key
    
    if active_key:
        os.environ["GROQ_API_KEY"] = active_key

# Load Bronze DB based on selection
if selected_db_path and os.path.exists(selected_db_path):
    shutil.copyfile(selected_db_path, "bronze.db") 
elif dataset_choice != "Custom Upload (CSV/Excel)":
    st.error("Datasets not found! The server may be restarting. Refresh the page.")
    st.stop()

# --- Pipeline Execution ---
st.divider()
st.header("🛠️ Execute Zero-Trust Pipeline")

if st.button("Execute AI Data Masking Pipeline 🚀", use_container_width=True):
    st.session_state.gold_ready = False
    st.session_state.messages = []
    st.session_state.dynamic_questions = []
    
    with st.spinner(f"Agent is dynamically parsing the schema and carefully masking PII..."):
        success = mask_data_with_groq(config.BRONZE_DB_URI)
        if success:
            st.session_state.gold_ready = True
            st.success("✅ PII Masked successfully! Data safely migrated to Gold DB.")
        else:
            st.error("Masking failed. Check logs.")

st.write("") 

# ==========================================
# --- TAB LAYOUT (App View vs Architecture) ---
# ==========================================
tab_app, tab_architecture = st.tabs(["🚀 Application View", "🏗️ System Architecture"])

with tab_app:
    # --- 1. Medallion Pipeline (STACKED VERTICALLY) ---
    st.header("📊 Medallion Architecture Comparison")

    engine_bronze = create_engine(config.BRONZE_DB_URI)
    try:
        df_bronze = pd.read_sql(f"SELECT * FROM {config.TABLE_NAME}", engine_bronze)
        engine_bronze.dispose() 
        
        st.markdown("### 🔴 Bronze Layer (Contains PII)")
        st.caption("Raw data ingested from upstream systems. HIGHLY SENSITIVE.")
        st.dataframe(df_bronze, height=350, use_container_width=True)
    except Exception:
        st.warning("Bronze layer data not available.")

    st.markdown("### 🟢 Gold Layer (AI-Ready)")
    if st.session_state.gold_ready:
        st.caption("Sanitized via Schema mapping. Safe for Analysts and Vector DBs.")
        
        engine_gold = create_engine(config.GOLD_DB_URI)
        df_gold = pd.read_sql(f"SELECT * FROM {config.TABLE_NAME}", engine_gold)
        engine_gold.dispose() 
        
        st.markdown(f"""
            <div class="print-safe-alert" style="padding: 1rem; border-radius: 0.5rem; background-color: #d1e7dd; color: #0f5132; margin-bottom: 1rem; border: 1px solid #badbcc;">
                <strong>✅ Rows Successfully Sanitized:</strong> {len(df_gold)} records
            </div>
        """, unsafe_allow_html=True)
        
        st.dataframe(df_gold, height=350, use_container_width=True)
    else:
        st.info("Click 'Execute AI Data Masking' above to generate Gold Layer data.")

    st.divider()

    # --- 2. Agentic BI Chat Interface ---
    if st.session_state.gold_ready:
        st.header("💬 Agentic BI: Text-to-SQL Analytics")
        st.markdown("The Agent is securely connected **only** to the masked Gold Database. Ask questions in natural language.")
        
        if not st.session_state.dynamic_questions:
            if not active_key:
                 st.warning("⚠️ Please provide a Groq API Key to generate suggested questions.")
            else:
                with st.spinner("🧠 AI is analyzing the schema & data to generate context-aware questions..."):
                    st.session_state.dynamic_questions = generate_dynamic_questions(config.GOLD_DB_URI)

        selected_suggestion = None
        if st.session_state.dynamic_questions:
            with st.expander("💡 Suggested Analytics Questions (Click to Ask)", expanded=True):
                for q in st.session_state.dynamic_questions:
                    if st.button(q, use_container_width=True):
                        selected_suggestion = q

        chat_container = st.container()

        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        user_input = st.chat_input(f"Ask an analytics question about the {dataset_choice} dataset...")
        actual_prompt = user_input or selected_suggestion

        if actual_prompt:
            st.session_state.messages.append({"role": "user", "content": actual_prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(actual_prompt)

                with st.chat_message("assistant"):
                    if not active_key:
                        error_msg = "🚨 **API Key Missing:** No active Groq API key found. Please enter one in the sidebar."
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    else:
                        with st.spinner("Analyzing schema and executing SQL..."):
                            try:
                                response = ask_sql_agent(actual_prompt)
                                lower_res = response.lower()
                                if "error" in lower_res and any(k in lower_res for k in ["429", "rate limit", "rate_limit", "quota", "exhausted"]):
                                    error_msg = "🚨 **API Limit Reached!** The default key has exhausted its daily quota. Please enter your own Groq API key in the sidebar under **Bring Your Own Key (BYOK)** to continue."
                                    st.toast("API Rate Limit Exhausted", icon="🚨")
                                    st.error(error_msg)
                                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                                elif response.startswith("Error"):
                                    st.error(response)
                                    st.session_state.messages.append({"role": "assistant", "content": response})
                                else:
                                    st.markdown(response)
                                    st.session_state.messages.append({"role": "assistant", "content": response})
                                    
                            except Exception as e:
                                error_msg = f"Error querying database: {str(e)}"
                                st.error(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
    else:
        st.info("Please execute the masking pipeline above before querying data.")

with tab_architecture:
    st.header("🏗️ System Architecture")
    st.markdown("This project adheres to the **Principle of Least Privilege** and uses a simulated **Medallion Data Architecture**.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.error("### 🔴 Phase 1: Ingestion\n**Bronze Database**")
        st.write("Raw data containing sensitive Personally Identifiable Information (PII) is ingested from internal enterprise systems.")
        st.write("🔒 *Strictly completely isolated from LLMs.*")
    with col_b:
        st.info("### 🛡️ Phase 2: Sanitization\n**AI Masking Pipeline**")
        st.write("An intelligent Python rules-engine combined with Data Engineering validates columns against Schema configurations.")
        st.write("Names, SSNs, and Emails are masked, while Categorical Dimensions and Metrics are safely preserved.")
    with col_c:
        st.success("### 🟢 Phase 3: Analytics\n**Gold Database**")
        st.write("A completely sanitized, AI-Ready database is generated.")
        st.write("🤖 *The LangChain Text-to-SQL Agent operates EXCLUSIVELY in this read-only layer to provide insights.*")

    st.divider()
    st.markdown("### 🧩 Technical Stack")
    st.markdown("""
    - **Frontend UI:** Streamlit
    - **LLM Engine:** Groq API (`openai/gpt-oss-20b`)
    - **Agent Framework:** LangChain (`create_sql_agent`)
    - **Data Pipeline:** Pandas, SQLAlchemy, SQLite
    """)