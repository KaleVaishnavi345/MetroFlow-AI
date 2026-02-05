from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import requests
import warnings
import json
from datetime import datetime, timedelta # Added timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import plotly.express as px
import plotly.io as pio

# --- INITIALIZE APP ---
app = Flask(__name__)
app.secret_key = "mumbai_metro_secret" 
warnings.filterwarnings("ignore")

# --- GLOBAL LIVE MEMORY ---
try:
    fleet_memory = pd.read_csv('metro_fleet_inventory.csv').to_dict(orient='records')
except:
    fleet_memory = [] 

system_logs = [f"[{datetime.now().strftime('%H:%M:%S')}] System Booted: AI Core Ready."]

def add_log(action):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_logs.append(f"[{timestamp}] {action}")

# --- API CONFIGURATION ---
API_KEY = "f99b3325008a9421b84a1c21685df9b4"
CITY = "Mumbai"

def get_live_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    try:
        data = requests.get(url).json()
        temp = data['main']['temp']
        condition = data['weather'][0]['main']
        weather_map = {"Clear": 0, "Clouds": 1, "Haze": 1, "Mist": 1, "Rain": 2, "Drizzle": 2, "Thunderstorm": 3}
        return temp, weather_map.get(condition, 0), condition
    except:
        return 28.0, 0, "Clear (Fallback)"

# --- AI BRAIN ---
def predict_smart_frequency():
    try:
        pass_df = pd.read_csv('passenger_demand_nov_dec_2025.csv')
        weather_df = pd.read_csv('weather_nov_dec_2025.csv')
        train_df = pd.merge(pass_df, weather_df, on='date')
        
        le = LabelEncoder()
        train_df['weather_enc'] = le.fit_transform(train_df['weather_condition'])
        train_df['target_freq'] = train_df['avg_daily_passengers'].apply(lambda x: 3 if x > 500000 else 8)
        
        X = train_df[['avg_daily_passengers', 'weather_enc', 'temperature_c']]
        y = train_df['target_freq']
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        live_temp, live_weather_enc, live_cond = get_live_weather()
        prediction = model.predict([[580000, live_weather_enc, live_temp]])[0]
        return int(round(prediction)), live_temp, live_cond
    except:
        return 5, 28.0, "Clear"

# --- HELPER: PERMANENT STORAGE ---
def save_timetable_to_disk(date_str, timetable_data, standby_rake):
    try:
        try:
            df = pd.read_csv('confirmed_schedules.csv')
        except:
            df = pd.DataFrame(columns=['date', 'schedule_json', 'standby'])
            
        df = df[df['date'] != date_str] # Remove duplicate date entry if exists
        
        new_entry = {
            'date': date_str,
            'schedule_json': json.dumps(timetable_data),
            'standby': standby_rake
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv('confirmed_schedules.csv', index=False)
        return True
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return False

# --- FLASK WEB ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'): return redirect(url_for('home'))
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'metro123':
            session['logged_in'] = True
            add_log("Manager authenticated.")
            return redirect(url_for('home'))
        return "Invalid Credentials. <a href='/login'>Try again</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if not session.get('logged_in'): return redirect(url_for('login'))
    temp, _, cond = get_live_weather()
    critical = [r['rake_id'] for r in fleet_memory if float(r['km_since_last_service']) >= 5000 or r['current_status'] == 'Maintenance']
    return render_template('index.html', temp=temp, cond=cond, logs=system_logs[-6:], alerts=critical)

@app.route('/generate')
def generate():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    gap, temp, cond = predict_smart_frequency()
    all_days_schedules = []
    
    # Mumbai Metro Line 1 Specifics
    route_length_km = 11.4 
    
    # 1. Start with the CURRENT real-world fleet state (deep copy)
    virtual_fleet = json.loads(json.dumps(fleet_memory)) 

    # We loop through 2 days (16th and 17th Jan)
    for i in range(1, 3):
        target_date = (datetime.now() + timedelta(days=i)).strftime("%d %b %Y")
        
        # A. Filter Rakes available AT THE START of this target date
        available = [r for r in virtual_fleet if r['current_status'] == 'Operational' and float(r['km_since_last_service']) < 5000]
        
        if not available:
            continue

        # B. Standby Logic: Pick the rake with the highest KM to rest today
        available.sort(key=lambda x: float(x['km_since_last_service']), reverse=True)
        day_standby_id = available[0]['rake_id']
        
        # C. Define Running Rakes: Everyone else is "Operational" and scheduled
        running_ids = [r['rake_id'] for r in available[1:]]
        running_ids.sort(key=lambda x: int(''.join(filter(str.isdigit, str(x))) or 0))

        # D. Generate Timetable for this specific day
        timetable = []
        current, end_time, serial = 330, 1425, 1
        while current <= end_time:
            is_peak = (480 <= current <= 600) or (1020 <= current <= 1200)
            day_gap = gap if is_peak else 8
            
            rake_assigned = running_ids[(serial - 1) % len(running_ids)]
            
            timetable.append({
                "Serial_No": serial,
                "Rake_No": rake_assigned,
                "Time": f"{current // 60:02d}:{current % 60:02d}",
                "Mode": "PEAK" if is_peak else "OFF-PEAK"
            })
            current += day_gap
            serial += 1
            
        # E. Store this day's results including the fleet's starting "health"
        all_days_schedules.append({
            "date": target_date, 
            "timetable": timetable, 
            "standby": day_standby_id,
            "fleet_state_at_start": json.loads(json.dumps(virtual_fleet)) 
        })

        # --- F. VIRTUAL AGING LOGIC (Triggers at the end of Day 1) ---
        # We update 'virtual_fleet' so that the NEXT iteration (Day 2) sees the new KM values
        for r in virtual_fleet:
            # If the rake was in today's running list, add distance based on trip count
            trips_done = sum(1 for row in timetable if row['Rake_No'] == r['rake_id'])
            distance_today = trips_done * route_length_km
            
            r['km_since_last_service'] = round(float(r['km_since_last_service']) + distance_today, 2)
            
            # Grounding Rule: If it hit the limit today, it's 'Maintenance' for tomorrow
            if r['km_since_last_service'] >= 5000:
                r['current_status'] = 'Maintenance'

    # Send both days' data to the frontend
    return render_template('schedule.html', schedules=all_days_schedules, temp=temp, cond=cond)
                    
@app.route('/commit_schedule', methods=['POST'])
def commit_schedule():
    data = request.json
    if save_timetable_to_disk(data.get('date'), data.get('timetable'), data.get('standby')):
        add_log(f"LOCKED: Timetable for {data.get('date')} saved to disk.")
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

@app.route('/inventory')
def inventory():
    if not session.get('logged_in'): return redirect(url_for('login'))
    global fleet_memory
    df = pd.DataFrame(fleet_memory)
    fig = px.bar(df, x='rake_id', y='km_since_last_service', title="Fleet Health Status",
                 color='current_status', color_discrete_map={'Operational': '#28a745', 'Maintenance': '#dc3545'})
    return render_template('inventory.html', chart_html=pio.to_html(fig, full_html=False), inventory_data=fleet_memory)

@app.route('/approve_inventory', methods=['POST'])
def approve_inventory():
    global fleet_memory
    data = request.json 
    for entry in data:
        for rake in fleet_memory:
            if str(rake['rake_id']).strip() == str(entry['rake_id']).strip():
                # Rule: Auto-Reset KM if moving from Maintenance to Operational
                if rake['current_status'] == 'Maintenance' and entry['status'] == 'Operational':
                    rake['km_since_last_service'] = 0
                else:
                    rake['km_since_last_service'] = float(entry['km'])
                
                # Rule: Force Maintenance if KM > 5000
                rake['current_status'] = 'Maintenance' if rake['km_since_last_service'] >= 5000 else entry['status']

    pd.DataFrame(fleet_memory).to_csv('metro_fleet_inventory.csv', index=False)
    add_log("FLEET UPDATE: Inventory synced and saved.")
    return jsonify({"status": "success"})

@app.route('/approve_schedule', methods=['POST'])
def approve_schedule():
    add_log("BROADCAST: Live schedule updated.")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)