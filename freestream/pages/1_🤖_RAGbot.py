import os

import streamlit as st
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pages.utils.utility_funcs import (
    PrintRetrievalHandler,
    StreamHandler,
    RetrieveDocuments,
    set_llm,
    clear_messages,
)
from pages.utils.styles import footer

# Initialize LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "FreeStream-v3.0.0"
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets.LANGCHAIN.LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = st.secrets.LANGCHAIN.LANGCHAIN_API_KEY

# Set up page config
st.set_page_config(page_title="FreeStream: RAGbot", page_icon="🤖")
st.title("🤖RAGbot")
st.header(":green[_Retrieval Augmented Generation Chatbot_]", divider="red")
st.caption(":violet[_Ask Your Documents Questions_]")
# Show footer
st.markdown(footer, unsafe_allow_html=True)

# Add sidebar
st.sidebar.subheader("__User Panel__")
# Add file-upload button
uploaded_files = st.sidebar.file_uploader(
    label="Upload a PDF or text file",
    type=["pdf", "doc", "docx", "txt"],
    help="Types supported: pdf, doc, docx, txt",
    accept_multiple_files=True,
)
if not uploaded_files:
    st.info("Please upload documents to continue.")
    st.stop()

retrieve_docs = RetrieveDocuments(uploaded_files)
retriever = retrieve_docs.configure_retriever()

# Add temperature header
temperature_header = st.sidebar.markdown(
    """
    ## Temperature Slider
    """
)
# Add the sidebar temperature slider
temperature_slider = st.sidebar.slider(
    label=""":orange[Set LLM Temperature]. The :blue[lower] the temperature, the :blue[less] random the model will be. The :blue[higher] the temperature, the :blue[more] random the model will be.""",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.05,
    key="llm_temperature",
)

# Setup memory for contextual conversation
msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(
    memory_key="chat_history", chat_memory=msgs, return_messages=True
)

# Create a dictionary with keys to chat model classes
model_names = {
    "GPT-3.5 Turbo": ChatOpenAI(  # Define a dictionary entry for the "ChatOpenAI GPT-3.5 Turbo" model
        model="gpt-3.5-turbo-0125",  # Set the OpenAI model name
        openai_api_key=st.secrets.OPENAI.openai_api_key,  # Set the OpenAI API key from the Streamlit secrets manager
        temperature=temperature_slider,  # Set the temperature for the model's responses using the sidebar slider
        streaming=True,  # Enable streaming responses for the model
        max_tokens=4096,  # Set the maximum number of tokens for the model's responses
        max_retries=1,  # Set the maximum number of retries for the model
    ),
    "Gemini-Pro": ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=st.secrets.GOOGLE.google_api_key,
        temperature=temperature_slider,
        top_k=50,
        top_p=0.7,
        convert_system_message_to_human=True,
        max_output_tokens=4096,
        max_retries=1,
    ),
}

# Create a dropdown menu for selecting a chat model
selected_model = st.selectbox(
    label="Choose your chat model:",  # Set the label for the dropdown menu
    options=list(model_names.keys()),  # Set the available model options
    key="model_selector",  # Set a unique key for the dropdown menu
    on_change=lambda: set_llm(
        st.session_state.model_selector, model_names
    ),  # Set the callback function
)

# Load the selected model dynamically
llm = model_names[
    selected_model
]  # Get the selected model from the `model_names` dictionary

# Create a chain that ties everything together
qa_chain = ConversationalRetrievalChain.from_llm(
    llm, retriever=retriever, memory=memory, verbose=True
)

# Create a button to clear message history
st.sidebar.divider()  # Divder accentuation
st.sidebar.button(
    label="Clear message history",
    on_click=clear_messages(msgs),
    help="Erase all messages in the conversation history.",
    key="clear_messages_button",
    use_container_width=True,
)

# Display coversation history window
avatars = {"human": "user", "ai": "assistant"}
for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

# Display user input field and enter button
if user_query := st.chat_input(placeholder="Ask me anything!"):
    st.chat_message("user").write(user_query)

    # Display assistant response
    with st.chat_message("assistant"):
        # Check for the presence of the "messages" key in session state
        if "messages" not in st.session_state:
            st.session_state.messages = []

        retrieval_handler = PrintRetrievalHandler(st.container())
        stream_handler = StreamHandler(st.empty())
        response = qa_chain.run(
            user_query, callbacks=[retrieval_handler, stream_handler]
        )
        # Force Gemini's message to display
        # I'm unsure why it doesn't work like GPT-3.5
        if selected_model == "Gemini-Pro":
            st.write(response)
        st.toast("Success!", icon="✅")
