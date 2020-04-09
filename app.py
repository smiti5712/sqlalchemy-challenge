import numpy as np
import datetime as dt

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from flask import Flask, jsonify


#################################################
# Database Setup
#################################################
engine = create_engine("sqlite:///Resources/hawaii.sqlite")

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(engine, reflect=True)
Base.classes.keys()
# Save reference to the table
Measurement = Base.classes.measurement
Station = Base.classes.station

#################################################
# Flask Setup
#################################################
app = Flask(__name__)

#################################################
# Flask Routes
#################################################

@app.route("/")
def welcome():
    """List all available api routes."""
    return (
        f"<h2>Welcome to Surf's Up!: Hawaii's Climate API</h2>"
        f"This page refers to Hawaii's climate data ranging from 2010-01-01 until 2017-08-23<br/>"
        f"<h3>Available Routes:</h3>"
        f"<h4>/api/v1.0/precipitation</h4>"
        f"* This page lists last 12 months of precipitation(in Inches) data.<br/>"
        f"<h4>/api/v1.0/stations</h4>"
        f"* This page lists stations information.<br/>"
        f"<h4>/api/v1.0/tobs</h4>"
        f"* This page lists the dates and temperature observations (in degrees Fahrenheit) for the most active station "
        f"for the last year of data.<br/>"
        f"<h4>/api/v1.0/Startdate/Enddate</h4>"
        f"* This page expects start date or a combination of start and end date in yyyy-mm-dd format,"
        f"note that start date cannot be greater than 2017-08-23.<br/>"
        f"for e.g <br/>"
        f"<h5>/api/v1.0/2017-01-01</h5>"
        f"* It will give the minimum ,  average , and the max temperature for the date range greater than and equal "
        f"to 2017-01-01<br/><br/>" 
        f"<h5>/api/v1.0/2017-01-01/2017-02-01</h5>"
        f"* If a start date and end date is provided, this will give the minimum ,  average ,"
        f"and the max temperature in the date range 2017-01-01 and 2017-02-01(inclusive)"
            )

@app.route("/api/v1.0/precipitation")
def precipitation():
    # Create our session (link) from Python to the DB
    session = Session(engine)
      
    # get latest date
    latest_date = session.query(Measurement.date).order_by(Measurement.date.desc()).first()

    #using ravel to extract string from the above query object
    latest_date = list(np.ravel(latest_date))[0]

    #converting the string returned above to datetime format
    latest_date = dt.datetime.strptime(latest_date, '%Y-%m-%d')

    #calculating the date 1 years ago using timedelta
    date_year_ago = (latest_date - dt.timedelta(days=365)).date()

    # Perform a query to retrieve the data and precipitation scores
    prcp_result = session.query(Measurement.date,Measurement.prcp).\
                    filter(Measurement.date >= date_year_ago ).all()

    session.close()

    # Create a dictionary from the row data and append to a list of precipilation result
    prcp_result_list = []
    for date,prcp in prcp_result:
        prcp_dict = {date: prcp}
        prcp_result_list.append(prcp_dict)

    return jsonify(prcp_result_list)

@app.route("/api/v1.0/stations")
def station():
    # Create our session (link) from Python to the DB
    session = Session(engine)
    station_data = session.query(Station.station,Station.name,Station.latitude,Station.longitude,Station.elevation).all()
    session.close()
    station_data_list =[]
    for station,name,lat,lng,elevation in station_data:
        stattion_dict = {}
        stattion_dict["Station id"] = station
        stattion_dict["Station Name"] = name
        stattion_dict["Lat"] = lat
        stattion_dict["lng"] = lng
        stattion_dict["elevation"] = elevation
        station_data_list.append(stattion_dict)
    
    return jsonify(station_data_list)

@app.route("/api/v1.0/tobs")
def tobs():
    session = Session(engine)
    #get station with most temperature observations
    st_with_most_temp_obs = session.query(Measurement.station, func.count(Measurement.tobs))\
                        .group_by(Measurement.station)\
                        .order_by(func.count(Measurement.tobs).desc())\
                        .first()

    station_id = st_with_most_temp_obs[0]

    # get latest date
    latest_date_for_station = session.query(Measurement.date).filter(Measurement.station == station_id)\
                          .order_by(Measurement.date.desc()).first()

    #using ravel to extract string from the above query object
    latest_date_for_station = list(np.ravel(latest_date_for_station))[0]

    #converting the string returned above to datetime format
    latest_date_for_station = dt.datetime.strptime(latest_date_for_station, '%Y-%m-%d')

    #calculating the date 1 years ago using timedelta
    date_year_ago_for_station = (latest_date_for_station - dt.timedelta(days=365)).date()

    # Temperature Observations for the station for last 12 months
    Temp_result = session.query(Measurement.station,Station.name,Measurement.date, Measurement.tobs).\
                    filter(Measurement.station == Station.station ).\
                    filter(Measurement.date >= date_year_ago_for_station ).\
                    filter(Measurement.station == station_id).all()
    session.close()
    
    tobs_list =[]
    for station,name,date,tobs in Temp_result:
        tobs_dict = {}
        tobs_dict["Station id"] = station
        tobs_dict["Station name"] = name
        tobs_dict["date"] = date
        tobs_dict["temp"] = tobs
        tobs_list.append(tobs_dict)
    
    return jsonify(tobs_list)

@app.route('/api/v1.0/<startdate>')
def start(startdate):
    startdate = dt.datetime.strptime(startdate, '%Y-%m-%d').date()
    session = Session(engine)
    sel = [func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)]

    results =  (session.query(*sel)
                       .filter(func.strftime("%Y-%m-%d", Measurement.date) >= startdate).all())
    session.close()

    results_list = []                       
    for tmin,tavg,tmax in results:
        start_date_dict = {}
        start_date_dict["TMIN"] = tmin
        start_date_dict["TAVG"] = tavg
        start_date_dict["TMAX"] = tmax
        results_list.append(start_date_dict)

    if startdate < dt.datetime.strptime('2017-08-24', '%Y-%m-%d').date():
        return jsonify(results_list)
    else:
        return jsonify({"error": f"No data available for dates greater than 2017-08-23"}), 404

@app.route('/api/v1.0/<startdate>/<enddate>')
def startEnd(startdate, enddate):
    startdate = dt.datetime.strptime(startdate, '%Y-%m-%d').date()
    enddate = dt.datetime.strptime(enddate, '%Y-%m-%d').date()
    session = Session(engine)
    sel = [func.min(Measurement.tobs), func.avg(Measurement.tobs), func.max(Measurement.tobs)]

    results =  (session.query(*sel)
                       .filter(func.strftime("%Y-%m-%d", Measurement.date) >= startdate)\
                       .filter(func.strftime("%Y-%m-%d", Measurement.date) <= enddate).all())
    session.close()
    results_list = []                          
    for tmin,tavg,tmax  in results:
        start_end_date_dict = {}
        start_end_date_dict["TMIN"] = tmin
        start_end_date_dict["TAVG"] = tavg
        start_end_date_dict["TMAX"] = tmax
        results_list.append(start_end_date_dict)

    if startdate < dt.datetime.strptime('2017-08-24', '%Y-%m-%d').date() and startdate <= enddate:
        return jsonify(results_list)
    else:
        return jsonify({"error": f"No data available , check the date range provided"}), 404

if __name__ == '__main__':
    app.run(debug=True)