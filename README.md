# People Counting and High-Risk Area Monitoring System (Assesment For Middle AI Engineer Position)



https://github.com/user-attachments/assets/b254a5f6-6e6a-45d9-b1c4-7e7cfe1578a9



## 1. Project Overview

This project is an end-to-end system designed to perform real-time object detection, tracking, and people counting within user-defined polygonal areas from a video feed. The system is composed of a backend API for data management, a web-based dashboard for live monitoring and configuration, and a PostgreSQL database for persistent storage. The primary goal is to monitor the number of people entering and exiting high-risk zones.

## 2. Feature Checklist

This checklist outlines the features implemented in the project.

| Feature                      | Status | Notes                                                                                                                               |
| ---------------------------- | :----: | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Database Design** |  ✅    | A PostgreSQL database schema is implemented to store area configurations and time-stamped entry/exit events.               |
| **Dataset Collection** |  ✅    | The system supports both static video file uploads and live RTSP/HTTP stream URLs as data sources.                       |
| **Object Detection & Tracking** |  ✅    | Human detection and tracking(ByteTrack) is handled using a pre-trained YOLO model from the `ultralytics` library.             |
| **Counting & Polygon Area** |  ✅    | The dashboard provides a canvas to draw dynamic polygon areas. The system accurately counts entries and exits from these zones. |
| **API Integration** |  ✅    | A complete FastAPI backend provides endpoints for area management and statistics retrieval.                                 |
| **Deployment** |  ✅    | The entire application stack is containerized using Docker and Docker Compose for easy testing.         |

## 3. System Architecture

### 3.1. System Design Diagram

<img width="474" height="566" alt="sdd drawio" src="https://github.com/user-attachments/assets/67ed3274-9ed3-43c5-96d0-b1ba256de7f8" />

### 3.2. Database Schema (ERD)

<img width="472" height="532" alt="dbb drawio" src="https://github.com/user-attachments/assets/5859267d-baf8-44e4-af05-88303f4776ee" />

### 3.3. End to end process
Video File or Live Stream URL → Read Video Frame via OpenCV → Detect & Track Persons using YOLOv8 Model → For each uniquely tracked person → Calculate Bounding Box Bottom-Center Point → Check if Point is Inside Defined Polygon → Compare current position with previous frame's position → Create 'CountingEvent' Object with type 'entry' or 'exit' → Add Event to a temporary batch list → Commit the batch of events to the database → Read Video Frame via OpenCV

## 4. Dataset
Here are a list of video used for testing:

https://www.youtube.com/watch?v=YzcawvDGe4Y

https://www.youtube.com/results?search_query=people+entering+and+leaving+stock+video

https://www.youtube.com/watch?v=-rtIP5Jrk58

https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8

https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8

https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8

## 5. Technology Stack

| Component         | Technology                               |
| ----------------- | ---------------------------------------- |
| **Backend** | FastAPI, Uvicorn            |
| **Frontend** | Streamlit                   |
| **Database** | PostgreSQL                  |
| **Object Detection**| YOLO (via `ultralytics`) |
| **Containerization**| Docker, Docker Compose          |
| **Core Libraries** | OpenCV, SQLAlchemy, Pydantic, Requests |

## 6. Setup and Installation (Docker)

The recommended way to run this project is by using Docker and Docker Compose, which ensures a consistent and reliable environment.

### Prerequisites

* Docker
* Docker Compose (usually included with Docker Desktop)

### Step 1: Clone the Repository

```
git clone <https://github.com/bryan-sto/People-Counting-and-High-Risk-Area-Monitoring-System-Assesment-For-Middle-AI-Engineer-Position-.git>
cd <your-repository-name>
```
Step 2: Configure Environment Variables

This project uses a .env file to manage configuration. Create one from the provided example.
Open the .env file and change yourpassword to a secure password of your choice. The file should look like this:

Code snippet
```
DATABASE_URL=postgresql://postgres:yourpassword@db:5432/people_counter_db
API_URL=http://api:8000
```

Step 3: Download the YOLO Model

The system is configured to use a YOLO model file named yolo11n.pt. Please download the appropriate model file from the official Ultralytics repository or your chosen source and place it in the root of the project directory.

Step 4: Build and Run the Application

Use Docker Compose to build the images and start all the services. This command will take a while on the first run(20-30 Minutes).
```
docker-compose up --build
```
Step 5: Access the Services

Once the containers are running, you can access the application:

    Dashboard: http://localhost:8501

    API Documentation: http://localhost:8000/docs

## 7. Project Structure

The project directory is organized as follows:
```
.
├── .dockerignore       # Specifies files for Docker to ignore
├── .env                # Stores environment variables for configuration
├── Dockerfile          # Blueprint for building the application image
├── api.py              # The FastAPI backend server
├── config.py           # Application configuration file
├── dashboard.py        # The Streamlit frontend application
├── database.py         # Database models and session setup
├── docker-compose.yml  # Defines and orchestrates the application services
└── requirements.txt    # Lists of all Python dependencies
```
## 8. API Endpoints

The following endpoints are exposed by the FastAPI backend.
|Method	|Path	|Description|
|-------|-----|-----------|
|POST	|/api/areas/	|Creates a new monitored area with a name and coordinates.|
|GET	|/api/areas/	|Retrieves a list of all configured areas.|
|DELETE	|/api/areas/{area_id}|	Deletes a specified area and all its associated event data.|
|GET	|/api/stats/{area_id}	|Gets total entry/exit counts for an area, with optional date filtering.|
|GET	|/api/stats/live/{area_id}	|Returns the most recent entry/exit event for a specific area.|

## 9. How To Use The Draw Area Function

1. Start Drawing: Move your mouse to the first corner of the desired area on the image and left-click once. This will place the first point of your polygon.

2. Add More Points: Move the mouse to the next corner of your area and left-click again. A line will connect the two points. Repeat this step for each corner of your shape. You need at least three points to form a valid area.

3. Complete the Shape: To finish drawing, move your mouse to the location of your final point and right click. The polygon will automatically close and fill with color.

4. Save the Area: Once the completed shape is visible, type a unique name for the area in the text box below the canvas and click the "Save Area" button.
   
5. Due to framework limitation i was not able to make the drawable area 100% to scale with the original video source

## 10. Issues
# Please do not hesitate to contact me through email bryanxavet@gmail.com if there's any issue/bug or any feature that doesnt met the requirement for this test
