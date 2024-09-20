import streamlit as st
import sqlitecloud
import pytz
from datetime import datetime


# Initialize session state variables for progress tracking
if 'daily_annotated' not in st.session_state:
    st.session_state.daily_annotated = 0
if 'total_annotated' not in st.session_state:
    st.session_state.total_annotated = 0

# Predefined list of valid annotator IDs
first = st.secrets["Annotatorid"]["first"]
second = st.secrets["Annotatorid"]["second"]
third = st.secrets["Annotatorid"]["third"]
forth = st.secrets["Annotatorid"]["forth"]
fifth = st.secrets["Annotatorid"]["fifth"]
valid_annotator_ids = [first, second, third, forth, fifth]

# Capture annotator ID at the start and store it in session state
if 'annotator_id' not in st.session_state:
    st.session_state.annotator_id = None

# Create a text input for the annotator ID
annotator_id_input = st.text_input("أدخل معرف المراجع (Annotator ID):")

# Update the session state once the annotator ID is entered
if annotator_id_input:
    st.session_state.annotator_id = annotator_id_input

# Check if the entered ID is valid
if st.session_state.annotator_id not in valid_annotator_ids:
    st.error("معرف المراجع غير صحيح. يرجى إدخال معرف صالح.")
    st.stop()  # Stop execution until a valid ID is provided

# Initialize a list to store token mappings if not already done
if 'token_mappings' not in st.session_state:
    st.session_state.token_mappings = []


# Function to get the current time in the user's timezone
def get_local_time():
    user_timezone = pytz.timezone('Asia/Riyadh')
    local_time = datetime.now(user_timezone)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp


# Function to establish a fresh database connection
def get_db_connection():
    db_connect = st.secrets["dbcloud"]["db_connect"]
    db_name = st.secrets["dbcloud"]["db_name"]
    conn = sqlitecloud.connect(db_connect)
    conn.execute(f"USE DATABASE {db_name}")
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

# Function to save the annotation with the annotator ID and localized datestamp
def save_annotation(word, context):
    annotator_id = st.session_state.annotator_id  # Retrieve annotator ID from session state
    conn = get_db_connection()
    c = conn.cursor()

    # Get the current timestamp in the user's timezone
    local_timestamp = get_local_time()

    # Insert the annotation with the local timestamp
    c.execute('''
        INSERT INTO annotation_words_contexts (word, context, annotator_id, datestamp)
        VALUES (?, ?, ?, ?)
    ''', (word, context, annotator_id, local_timestamp))

    conn.commit()
    conn.close()  # Close the connection after saving

    # Update progress
    st.session_state.daily_annotated += 1
    st.session_state.total_annotated += 1


# Function to tokenize text into words (simple whitespace tokenization)
def tokenize(text):
    return text.split()


def display_matching_contexts(selected_word):
    conn = get_db_connection()
    c = conn.cursor()

    # Query annotation_words_contexts table
    c.execute('''
        SELECT 'annotation_words_contexts' as source, context as text FROM annotation_words_contexts 
        WHERE context LIKE ? 
        AND instr(context, ?) > 0
    ''', (f'%{selected_word}%', selected_word))
    annotation_results = c.fetchall()

    conn.close()

    total_results = len(annotation_results)

    # Display the total number of results
    st.write(f"عدد الجمل المدخلة لهذه الكلمة = {total_results} وأدناه أمثلة عليها:")

    # Display the results
    if annotation_results:
        for result in annotation_results:
            source, text = result
            st.write(f"- {text}")


# Function to handle saving the text and clearing the input
def process_text_callback():
    # Check if token mappings exist
    if not st.session_state.token_mappings:
        st.session_state.show_warning = True  # Set a flag to show the warning
        return  # Do not proceed if no token mappings have been made
    else:
        st.session_state.show_warning = False  # Reset the warning flag if mappings exist

    # We only want to save the selected token (from the token mappings)
    for token_mapping in st.session_state.token_mappings:
        selected_token, context = token_mapping.split(" -> ")

        # Save only the selected token and the corresponding context
        save_annotation(selected_token, context)

    # Clear token mappings after processing
    st.session_state.token_mappings = []


# Function to display the text box and save annotations
def display_token_mapping():
    # Initialize the session state for user text if not already done
    if 'user_text' not in st.session_state:
        st.session_state.user_text = ""

    # Text box for the user to input their text
    user_text = st.text_input("أدخل الجملة:", key="user_text")

    if user_text:
        # Dropdown to select a word from the entered text
        st.markdown(f'<p style="color:#F39C12; font-weight:bold;">اختر كلمة من الجملة:</p>', unsafe_allow_html=True)
        selected_word = st.selectbox("اختر كلمة", tokenize(user_text))

        # Query the database for this selected word as a whole word
        display_matching_contexts(selected_word)

        # Button to map the selected tokens
        if st.button("تعيين ارتباط"):
            st.session_state.token_mappings.append(f"{selected_word} -> {user_text}")

        # Display the list of all token mappings
        if st.session_state.token_mappings:
            st.write("تم تعيين الارتباطات التالية:")
            for mapping in st.session_state.token_mappings:
                st.write(mapping)

            # Option to save the annotation (word and context)
            if st.button("حفظ التعليق"):
                process_text_callback()  # Call the function to save and clear the input
                st.success("تم حفظ التعليق بنجاح!")

    # Button to clear the text input field
    def clear_text():
        st.session_state["user_text"] = ""

    st.button("كلمة جديدة", on_click=clear_text)  # Add the "New Word" button to reset the text box

# RTL Styling for Arabic and button enhancement
st.markdown("""
    <style>
    .stApp {
        direction: RTL;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# Display the token mapping interface
display_token_mapping()