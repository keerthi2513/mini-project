import pyodbc
from flask import Flask, render_template, request

app = Flask(__name__)

conn = pyodbc.connect(
    'DRIVER={SQL Server};'
    'SERVER=LAPTOP-RN45P3S7\\SQLEXPRESS;'
    'DATABASE=pollution_db;'
    'Trusted_Connection=yes;'
)

cursor = conn.cursor()

def get_suggestion(pollution_type):
    if pollution_type == "Vehicle Smoke":
        return "Avoid peak traffic hours and wear masks."
    elif pollution_type == "Garbage Burning":
        return "Avoid the area and report burning activities."
    elif pollution_type == "Construction Dust":
        return "Keep windows closed and use masks."
    elif pollution_type == "Factory Emissions":
        return "Stay indoors and use air purifiers."
    else:
        return "Stay safe and avoid polluted areas."

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':

        name = request.form['name']
        area = request.form['area']
        pollution_type = request.form['type']
        description = request.form['description']
        date = request.form['date']

        # 🚫 1. Description validation
        if len(description) < 10:
            return render_template(
                "error.html",
                message="Please provide a detailed description (minimum 10 characters)."
            )

        # 🚫 2. Duplicate check
        cursor.execute("""
            SELECT * FROM complaints 
            WHERE area = ? AND date = ? AND description = ?
        """, (area, date, description))

        existing = cursor.fetchone()

        if existing:
            return render_template(
                "error.html",
                message="Duplicate complaint detected!"
            )

        # ✅ Suggestion logic
        suggestion = get_suggestion(pollution_type)

        # ✅ Insert into DB (FIXED)
        cursor.execute(
            "INSERT INTO complaints (name, area, pollution_type, description, date) VALUES (?, ?, ?, ?, ?)",
            (name, area, pollution_type, description, date)
        )

        conn.commit()

        return render_template("success.html", suggestion=suggestion)

    return render_template('submit.html')
    
@app.route('/analysis')
def analysis():
    print("🔥 ANALYSIS ROUTE HIT")
    area_filter = request.args.get("area")
    type_filter = request.args.get("type")
    query = "SELECT area, COUNT(*) FROM complaints WHERE 1=1"
    params = []

    if area_filter:
        query += " AND area LIKE ?"
        params.append(f"%{area_filter}%")

    if type_filter:
        query += " AND pollution_type = ?"
        params.append(type_filter)

    query += " GROUP BY area ORDER BY COUNT(*) DESC"

    cursor.execute(query, params)
    area_counts = cursor.fetchall()

    # 🔹 2. Build risk data
    risk_data = []
    for row in area_counts:
        area = row[0]
        count = row[1]

        if count <= 2:
            risk = "Low"
        elif count <= 4:
            risk = "Medium"
        else:
            risk = "High"

        risk_data.append((area, int(count), risk))

    # 🔹 3. Total complaints
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    # 🔹 4. Top area
    cursor.execute("""
        SELECT TOP 1 area, COUNT(*) as c 
        FROM complaints 
        GROUP BY area 
        ORDER BY c DESC
    """)
    top_area = cursor.fetchone()

    # 🔹 5. Top pollution type
    cursor.execute("""
        SELECT TOP 1 pollution_type, COUNT(*) as c
        FROM complaints
        GROUP BY pollution_type
        ORDER BY c DESC
    """)
    top_type = cursor.fetchone()

    # 🔹 6. Type distribution (for pie chart)
    query_type = """
    SELECT pollution_type, COUNT(*) 
    FROM complaints
    WHERE 1=1
    """
    params = []

    if area_filter:
        query_type += " AND area LIKE ?"
        params.append(f"%{area_filter}%")

    if type_filter:
        query_type += " AND pollution_type = ?"
        params.append(type_filter)

    query_type += " GROUP BY pollution_type"

    cursor.execute(query_type, params)
    type_data = cursor.fetchall()

    # 🔹 7. Area distribution (for bar chart)
    query_area = "SELECT area, COUNT(*) FROM complaints WHERE 1=1"
    params_area = []

    if area_filter:
        query_area += " AND area LIKE ?"
        params_area.append(f"%{area_filter}%")

    if type_filter:
        query_area += " AND pollution_type = ?"
        params_area.append(type_filter)

    query_area += " GROUP BY area ORDER BY COUNT(*) DESC"

    cursor.execute(query_area, params_area)
    area_data = cursor.fetchall()

    print("AREA COUNTS:", area_counts)
    print("RISK DATA:", risk_data)

    # 🔹 FINAL RENDER
    return render_template(
        "analysis.html",
        data=risk_data,
        total=total,
        top_area=top_area,
        top_type=top_type,
        type_data=type_data,
        area_data=area_data
    )

@app.route('/type_analysis')
def type_analysis():

    cursor.execute("""
        SELECT pollution_type, COUNT(*) as total 
        FROM complaints 
        GROUP BY pollution_type 
        ORDER BY total DESC
    """)

    data = cursor.fetchall()

    return render_template("type.html", data=data)

@app.route('/trend')
def trend():
    cursor.execute("""
        SELECT date, COUNT(*) as total 
        FROM complaints 
        GROUP BY date 
        ORDER BY date
    """)
    
    data = cursor.fetchall()

    return render_template('trend.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
