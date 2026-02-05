# MetroFlow AI: Dynamic Operational & Fleet Management System

### 🚆 Project Overview
**MetroFlow AI** is an intelligent scheduling and maintenance proposal for **Mumbai Metro Line 1**. It leverages Machine Learning to bridge the gap between static timetables and real-world operational variables like weather and mechanical wear.

---

### 🚀 Key Features (Proposed)
* **AI-Driven Scheduling:** Utilizing **Random Forest Regression** to adjust train frequency based on live Mumbai weather APIs.
* **Digital Twin Logic:** Implementing a **Virtual Aging** algorithm to track rake mileage mathematically ($1 \text{ trip} = 11.4 \text{ km}$).
* **Predictive Maintenance:** Automated system alerts and grounding when a rake hits the **5,000 km safety threshold**.
* **Managerial Dashboard:** A web-based interface for 48-hour forecasting and fleet rotation.

---

### 🛠️ Technical Stack
* **Language:** Python 3.x
* **Framework:** Flask (Backend), Streamlit (Frontend/Demo)
* **Machine Learning:** Scikit-learn (Random Forest)
* **Version Control:** Git & GitHub

---

### 📈 Proposed Workflow
1. **Data Ingestion:** Fetching live weather data and current rake mileage.
2. **Analysis:** ML model predicts optimal "Gap" (minutes between trains).
3. **Simulation:** Virtual Aging logic updates the mileage of active rakes.
4. **Output:** A 48-hour schedule is generated and displayed on the dashboard.



