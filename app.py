import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="CodeBuddy AI", page_icon="🤖", layout="wide")

st.sidebar.title("CodeBuddy AI")
st.sidebar.markdown("Explain, convert, debug, and generate code with Gemini.")
choice = st.sidebar.radio("Navigation", ["Explain Code", "Generate Code", "Convert Code", "Debug Code"])

st.sidebar.markdown("---")
st.sidebar.info(
    "**Note:** Review and test any generated code before you use it. "
    "CodeBuddy only explains and suggests. It never runs your code."
)

# Models to try in order of priority if a 503 overload occurs
MODEL_CANDIDATES = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite"
]

def generate_with_fallback(client, prompt):
    """Tries models sequentially if a 503 high-demand error occurs."""
    for model_id in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_id, 
                contents=prompt
            )
            return response.text, model_id
        except APIError as e:
            if e.code == 503:
                continue
            raise e
        except Exception as e:
            if "503" in str(e):
                continue
            raise e
            
    raise Exception("All Gemini models are currently experiencing high demand. Please try again in a moment.")

if not api_key:
    st.error("GEMINI_API_KEY is missing. Add it to your .env file in the project folder, then restart the app.")
else:
    client = genai.Client(api_key=api_key)

    # --- TAB 1: EXPLAIN CODE & ASK DOUBTS ---
    if choice == "Explain Code":
        st.header("Explain Code & Ask Doubts")
        st.markdown("Paste your code to get an initial explanation, then ask follow-up doubts below!")

        # Session state for chat history
        if "explain_messages" not in st.session_state:
            st.session_state.explain_messages = []

        code_input = st.text_area("Your code:", height=150, key="code_input_area")

        if st.button("Generate Explanation"):
            if not code_input.strip():
                st.warning("Please enter some code to explain.")
            else:
                with st.spinner("Analyzing code..."):
                    try:
                        prompt = f"Explain the following code line by line in beginner-friendly English:\n\n{code_input}"
                        output_text, used_model = generate_with_fallback(client, prompt)
                        
                        # Store in history
                        st.session_state.explain_messages = [
                            {"role": "user", "content": f"Explain this code:\n```python\n{code_input}\n```"},
                            {"role": "assistant", "content": f"*(Model used: `{used_model}`)*\n\n{output_text}"}
                        ]
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

        # Display history
        for msg in st.session_state.explain_messages:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**CodeBuddy:** {msg['content']}")

        # Follow-up doubt input
        if st.session_state.explain_messages:
            st.markdown("---")
            followup = st.text_input("Have a doubt about this explanation? Type it here:")
            if st.button("Ask Doubt"):
                if followup.strip():
                    with st.spinner("Answering doubt..."):
                        try:
                            context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.explain_messages])
                            history_prompt = f"Given this conversation history:\n{context}\n\nUser doubt: {followup}\nProvide a clear, simple answer to this doubt."
                            output_text, used_model = generate_with_fallback(client, history_prompt)
                            
                            st.session_state.explain_messages.append({"role": "user", "content": followup})
                            st.session_state.explain_messages.append({"role": "assistant", "content": f"*(Model used: `{used_model}`)*\n\n{output_text}"})
                            st.rerun()
                        except Exception as e:
                            st.error(f"An error occurred: {e}")

    # --- TAB 2: GENERATE CODE ---
    elif choice == "Generate Code":
        st.header("Generate Code from Prompt")
        st.markdown("Describe what you want to build in plain English, choose your language, and let Gemini write the code.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            prompt_input = st.text_area("Describe your requirement:", height=150, placeholder="e.g., Write an Oracle PL/SQL block or query to fetch employees.")
        with col2:
            target_lang = st.selectbox("Target Language", ["Python", "JavaScript", "HTML/CSS", "Java", "C++", "SQL / Oracle PL/SQL"])
        
        if st.button("Generate Code"):
            if not prompt_input.strip():
                st.warning("Please enter a description of what you want to build.")
            else:
                with st.spinner("Generating code..."):
                    try:
                        full_prompt = f"Write clean, production-ready, well-commented {target_lang} code for the following requirement (if Oracle/PL-SQL is selected, ensure syntax is fully compatible with Oracle databases):\n\n{prompt_input}\n\nProvide clear code snippets with a brief explanation."
                        output_text, used_model = generate_with_fallback(client, full_prompt)
                        st.subheader("Generated Code")
                        st.caption(f"Generated using `{used_model}`")
                        st.markdown(output_text)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

    # --- TAB 3: CONVERT CODE ---
    elif choice == "Convert Code":
        st.header("Convert Code")
        col1, col2 = st.columns(2)
        with col1:
            source_lang = st.selectbox("Source language", ["Python", "JavaScript", "Java", "C++", "Oracle PL/SQL", "Standard SQL"])
        with col2:
            target_lang = st.selectbox("Target language", ["Python", "JavaScript", "Java", "C++", "Oracle PL/SQL", "Standard SQL"])
        
        code_input = st.text_area("Your code:", height=200)
        if st.button("Convert Code"):
            if not code_input.strip():
                st.warning("Please enter some code to convert.")
            else:
                with st.spinner("Converting code..."):
                    try:
                        prompt = f"Convert this {source_lang} code into {target_lang}. Ensure proper syntax rules (like Oracle PL/SQL conventions if target is Oracle). Return clean code with brief comments:\n\n{code_input}"
                        output_text, used_model = generate_with_fallback(client, prompt)
                        st.subheader("Converted Code")
                        st.caption(f"Generated using `{used_model}`")
                        st.markdown(output_text)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

    # --- TAB 4: DEBUG CODE ---
    elif choice == "Debug Code":
        st.header("Debug Code")
        st.markdown("Paste your error message or broken code along with the error to find out why it failed.")
        error_input = st.text_area("Error message or buggy code (mention if it's Oracle/PL-SQL):", height=200)
        if st.button("Debug Error"):
            if not error_input.strip():
                st.warning("Please enter an error message or code.")
            else:
                with st.spinner("Analyzing error..."):
                    try:
                        prompt = f"Explain this programming or database error/issue (handle Oracle database specific syntax errors if applicable), its likely cause, and provide a suggested corrected code fix:\n\n{error_input}"
                        output_text, used_model = generate_with_fallback(client, prompt)
                        st.subheader("Debugging Analysis & Fix")
                        st.caption(f"Generated using `{used_model}`")
                        st.markdown(output_text)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")