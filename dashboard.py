import streamlit as st
import cv2
import numpy as np
import requests
import pandas as pd
from PIL import Image
from ultralytics import YOLO
from streamlit_drawable_canvas import st_canvas
import os

# Import project modules
import config
from database import SessionLocal, CountingEvent

# --- Page and App Configuration ---
st.set_page_config(layout="wide", page_title="People Counting Dashboard")
st.title("People Counting System High-Risk Area Monitoring System")

# --- Constants ---
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DB_COMMIT_BATCH_SIZE = 5  # Number of events to batch before committing to DB

# --- API Helper Functions ---
def get_areas():
    """Fetches all configured areas from the API."""
    try:
        res = requests.get(f"{API_URL}/api/areas/")
        res.raise_for_status()
        return res.json()
    except requests.RequestException:
        return []

def get_stats(area_id):
    """Fetches lifetime statistics for a given area."""
    try:
        res = requests.get(f"{API_URL}/api/stats/{area_id}")
        res.raise_for_status()
        return res.json()
    except requests.RequestException:
        return {"entries": 0, "exits": 0}

def save_area_to_api(area_name, coordinates):
    """Sends a new area to the backend API to be saved."""
    payload = {"name": area_name, "coordinates": coordinates}
    try:
        response = requests.post(f"{API_URL}/api/areas/", json=payload)
        response.raise_for_status()
        st.success(f"✅ Successfully saved area '{area_name}'!")
        return True
    except requests.RequestException as e:
        st.error(f"❌ Error saving area: Could not connect to the API. Is it running?", icon="🚨")
        st.error(f"Details: {e}")
        return False

def delete_area_from_api(area_id: int):
    """Sends a delete request to the API for a specific area."""
    try:
        res = requests.delete(f"{API_URL}/api/areas/{area_id}")
        res.raise_for_status()
        st.success("Area deleted successfully.")
        return True
    except requests.RequestException as e:
        st.error(f"Error deleting area: {e}")
        return False

# --- Cached Resources ---
@st.cache_resource
def load_yolo_model(model_path: str) -> YOLO:
    """Loads the YOLO model from the specified path, caching it for performance."""
    return YOLO(model_path)

# --- Session State Initialization ---
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'page' not in st.session_state:
    st.session_state.page = "Live Processor"
if 'config_frame' not in st.session_state:
    st.session_state.config_frame = None

def stop_processing():
    """Callback function to stop processing when a new file is uploaded."""
    st.session_state.processing = False

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
if st.sidebar.button("🎥 Live Processor", use_container_width=True):
    st.session_state.page = "Live Processor"
if st.sidebar.button("📊 Statistics & Management", use_container_width=True):
    st.session_state.page = "Statistics & Management"


# ==============================================================================
# LIVE PROCESSOR PAGE (Updated with Defensive Check)
# ==============================================================================
if st.session_state.page == "Live Processor":
    st.header("🎥 Live Video Processor")

    col1, col2 = st.columns(2)
    with col1:
        areas = get_areas()
        if not areas:
            st.warning("No areas configured. Please go to the 'Statistics & Management' page to create one.")
            st.stop()
        
        area_options = {area['name']: area['id'] for area in areas}
        selected_area_name = st.selectbox("Select an Area to Monitor", options=area_options.keys())
        
        source_type = st.radio("Select Video Source", ("File Upload", "Live Feed URL (e.g., RTSP)"))
        video_source = None
        
        if source_type == "File Upload":
            uploaded_file = st.file_uploader(
                "Upload a video to process", 
                type=["mp4", "mov", "avi"], 
                on_change=stop_processing
            )
            if uploaded_file:
                with open("temp_video.mp4", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                video_source = "temp_video.mp4"
        else:
            video_source = st.text_input("Enter Live Feed URL")

    with col2:
        confidence_threshold = st.slider(
            "Detection Confidence Threshold", 
            min_value=0.0, max_value=1.0, value=0.3, step=0.05
        )
        st.write("")
        st.write("")

    if video_source:
        if not st.session_state.processing:
            if st.button("Start Processing", type="primary", use_container_width=True):
                st.session_state.processing = True
                st.rerun()
        else:
            if st.button("Stop Processing", use_container_width=True):
                st.session_state.processing = False
                st.rerun()

        stframe = st.empty()
        if not st.session_state.processing and source_type == "File Upload" and 'uploaded_file' in locals() and uploaded_file:
            stframe.video(uploaded_file)
        
        if st.session_state.processing:
            with st.spinner(f"Loading YOLO model from '{config.MODEL_PATH}'..."):
                model = load_yolo_model(config.MODEL_PATH)

            db = SessionLocal()
            selected_area_id = area_options[selected_area_name]
            area_config = next((area for area in areas if area['id'] == selected_area_id), None)

            if not area_config or 'coordinates' not in area_config:
                st.error(f"Could not load configuration for area '{selected_area_name}'.")
                st.stop()

            raw_coords = area_config['coordinates']
            clean_coords = [c for c in raw_coords if isinstance(c, (list, tuple)) and len(c) == 2]
            
            if len(clean_coords) < 3:
                st.error(f"The selected area '{selected_area_name}' has invalid polygon data (fewer than 3 points). Please delete and re-create it.")
                st.stop() # Stop execution to prevent a crash.

            polygon_coords = np.array(clean_coords, np.int32)
            cap = cv2.VideoCapture(video_source)
            person_positions, entry_count, exit_count = {}, 0, 0
            events_to_commit = []
            while cap.isOpened() and st.session_state.processing:
                success, frame = cap.read()
                if not success:
                    st.warning("Video feed ended or failed.")
                    break
                
                results = model.track(frame, persist=True, classes=0, conf=confidence_threshold, verbose=False)
                annotated_frame = results[0].plot()
                cv2.polylines(annotated_frame, [polygon_coords], isClosed=True, color=(0, 0, 255), thickness=3)
                
                if results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                    track_ids = results[0].boxes.id.cpu().numpy().astype(int)

                    for box, track_id in zip(boxes, track_ids):
                        bottom_center = (int((box[0] + box[2]) / 2), int(box[3]))
                        is_inside = cv2.pointPolygonTest(polygon_coords, bottom_center, False) >= 0
                        was_inside = person_positions.get(track_id, False)

                        if not was_inside and is_inside:
                            entry_count += 1
                            events_to_commit.append(CountingEvent(area_id=selected_area_id, event_type='entry', tracker_id=int(track_id)))
                        elif was_inside and not is_inside:
                            exit_count += 1
                            events_to_commit.append(CountingEvent(area_id=selected_area_id, event_type='exit', tracker_id=int(track_id)))
                        
                        person_positions[track_id] = is_inside
                        
                        if len(events_to_commit) >= DB_COMMIT_BATCH_SIZE:
                            db.add_all(events_to_commit)
                            db.commit()
                            events_to_commit.clear()
                
                cv2.putText(annotated_frame, f'Entries: {entry_count}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(annotated_frame, f'Exits: {exit_count}', (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                
                stframe.image(cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB))
            
            if events_to_commit:
                db.add_all(events_to_commit)
                db.commit()

            cap.release()
            db.close()
            st.success("Processing stopped.")
            st.session_state.processing = False
            st.rerun()

# ==============================================================================
# STATISTICS & MANAGEMENT PAGE
# ==============================================================================
elif st.session_state.page == "Statistics & Management":
    st.header("📊 Statistics & Management")
    
    st.subheader("Area Overview")
    if st.button("Refresh Data 🔄"):
        st.rerun()

    areas = get_areas()
    if not areas:
        st.info("No areas found. Use the configuration tool below to create one.")
    else:
        for area in areas:
            with st.container():
                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
                with c1:
                    st.subheader(area['name'])
                
                stats = get_stats(area['id'])
                with c2:
                    st.metric("Total Entries", stats.get('entries', 'N/A'))
                with c3:
                    st.metric("Total Exits", stats.get('exits', 'N/A'))
                with c4:
                    if st.button(f"❌ Delete", key=f"delete_{area['id']}", type="secondary", use_container_width=True):
                        if delete_area_from_api(area['id']):
                            st.rerun()
                st.divider()

    st.header("Configure New Area")
    st.info("Draw a new monitored area using a file upload or a live camera feed as a background.")

    tab1, tab2 = st.tabs(["Upload Background", "Use Live Stream"])

    with tab1:
        st.markdown("##### Upload a video or image file.")
        uploaded_file_config = st.file_uploader(
            "Upload",
            type=["mp4", "mov", "avi", "jpg", "png"],
            key="config_uploader",
            label_visibility="collapsed"
        )
        if uploaded_file_config:
            if uploaded_file_config.type.startswith('video/'):
                with open("temp_config_bg.mp4", "wb") as f:
                    f.write(uploaded_file_config.getbuffer())
                cap = cv2.VideoCapture("temp_config_bg.mp4")
                success, frame = cap.read()
                cap.release()
            else:
                frame = np.array(Image.open(uploaded_file_config).convert("RGB"))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB_BGR)
                success = True
            
            if success:
                st.session_state.config_frame = frame
            else:
                st.error("Could not read a frame from the uploaded video file.")

    with tab2:
        st.markdown("##### Fetch a frame from a live HTTP or RTSP stream.")
        stream_url = st.text_input("Stream URL (e.g., rtsp://... or http://...)", key="stream_url_input")
        if st.button("Fetch Frame", key="fetch_frame_button"):
            if stream_url:
                with st.spinner("Connecting to stream and fetching a frame..."):
                    try:
                        cap = cv2.VideoCapture(stream_url)
                        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                        success, frame = cap.read()
                        cap.release()
                        if success:
                            st.session_state.config_frame = frame
                            st.success("Frame fetched successfully!")
                        else:
                            st.error("Failed to fetch frame. Check the URL and network connection.", icon="🚨")
                            st.session_state.config_frame = None
                    except Exception as e:
                        st.error(f"An error occurred: {e}", icon="🚨")
                        st.session_state.config_frame = None
            else:
                st.warning("Please enter a stream URL.")
    
    if st.session_state.config_frame is not None:
        frame_to_draw = st.session_state.config_frame
        frame_rgb = cv2.cvtColor(frame_to_draw, cv2.COLOR_BGR2RGB)
        height, width, _ = frame_to_draw.shape

        st.subheader("Draw Your Polygon")
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=3,
            stroke_color="#FF0000",
            background_image=Image.fromarray(frame_rgb),
            height=height,
            width=width,
            drawing_mode="polygon",
            key="canvas",
        )
        
        if canvas_result.json_data and canvas_result.json_data["objects"]:
            points = canvas_result.json_data["objects"][0].get("path")
            if points and len(points) > 2:
                points_to_save = [p[1:3] for p in points]
                with st.form("save_area_form"):
                    area_name = st.text_input("Enter a name for this area *")
                    submitted = st.form_submit_button("💾 Save Area")
                    if submitted:
                        if area_name:
                            if save_area_to_api(area_name, points_to_save):
                                st.rerun()
                        else:
                            st.error("Area name is required.")