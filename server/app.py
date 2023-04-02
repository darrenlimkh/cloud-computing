import json
import boto3
import pickle
from flask_cors import CORS
from database.RDSdatabase import RDSdatabase
from flask import Flask, request, jsonify
import numpy as np

app = Flask(__name__)
cors = CORS(app)

with open("config.json", "r") as f:
    config = json.load(f)

########################################### CONNECT TO RDS ################################################
rdsDB = RDSdatabase(config['rds']['username'],
                    config['rds']['password'],
                    config['rds']['host'],
                    config['rds']['dbname'],
                    config['rds']['port'])
rdsDB.initialConfig()   # initial config

########################################### GET MODEL FOR PREDICTION ################################################
# Credentials should already by setup in ec2 instance
# If running locally, credentials can be found by starting AWS Learner's Lab and typing:
# cat ~/.aws/credentials 
# in the console
s3_session = boto3.Session(
    aws_access_key_id = config['aws_credentials']['access_key_id'],
    aws_secret_access_key = config['aws_credentials']['secret_access_key'],
    aws_session_token = config['aws_credentials']['token']
)
s3 = s3_session.client('s3')

bucket_name = config['s3']['bucket_name']
file_name = config['s3']['file_path']
location = 'tmp/xgb_breast_classifier.pkl'

s3.download_file(bucket_name, file_name, location)
model = pickle.load(open(location, "rb"))

########################################### REACT REQUESTS ##############################################

# NOTE: This route is needed for the default EB health check route
@app.route('/')  
def home():
    return "ok"


@app.route("/api/login", methods=['POST'])
def login():
    username = request.get_json()["username"]
    password = request.get_json()["password"]
    organisation = request.get_json()["organisation"]
    isLogin = request.get_json()["isLogin"]
    print(username, password)
    
    # TODO: use this portion for sql codes!
    # if (isLogin) {
    #     # TODO: handle login
    # } else {
    #     # TODO: handle register
    # }
    if not isLogin: 
    #     #register user
        rdsDB.createNewUser(username, password, organisation)
    # #user sign in 
    userEngine, userCursor = rdsDB.userSignIn(username, password)
    
    try:
        return jsonify(
            {
            "message": "Login Successful.",
            }
        ), 200
    except Exception as e:
        return jsonify({
            "message": "Login Failed."
        }), 500
    
        
@app.route("/api/form", methods=['POST'])
def form():
    values = request.get_json()
    patientDetails = {
    "patientID": values['patientID'],
    "firstName": values['patientFirstName'],
    "lastName": values['patientLastName'],
    "DOB": values['dob'],
    "date_of_service": values['dos'],
    "area_code": values['areaCode'],
    "phoneNum": values['phoneNumber'],
    "is_left_breast": values['isLeft'],
    "is_implant": values['isImplant'],
    "density": values['density'],
    "remarks": values['remarks'],
    "concavity_mean": values['concavityMean'],
    "concavity_SE": values['concavitySE'],
    "concavity_Worst": values['concavityWorst'],
    "area_mean": values['areaMean'],
    "area_SE": values['areaSE'],
    "area_worst": values['areaWorst'],
    "symmetry_mean": values['symmetryMean'],
    "texture_mean": values['textureMean'],
    "diagnosis": values['diagnosis'],
    "date_of_closure": values['date_of_closure']
}
    #to get username and password
    username = None
    password = None
    rdsDB.addPatientData(username, password,**patientDetails)
    
    # TODO: use this to update the RDS database!
    # variable names can be found on Form.js 
    try:
        return jsonify(
            {
            "message": "Login Successful.",
            }
        ), 200
    except Exception as e:
        return jsonify({
            "message": "Login Failed."
        }), 500
    
    #insert data 
        
@app.route("/api/predict", methods=['POST'])
def predict():
    values = request.get_json()
    data = [[float(values['concavityMean']), 
            float(values['areaSE']), 
            float(values['areaWorst']), 
            float(values['concavityWorst']), 
            float(values['concavitySE']),
            float(values['textureMean']),
            float(values['areaMean']),
            float(values['symmetryMean'])]]
    data = np.array(data).reshape((1, 8))
    result = model.predict_proba(data)
    try:
        result = model.predict_proba(data)
        print("result:", np.round(float(result[:, 1][0]), 2))
        return jsonify(
            {
            "message": "Prediction Successful.",
            "prediction": np.round(float(result[:, 1][0]), 2)
            }
        ), 200
    except Exception as e:
        return jsonify({
            "message": "Prediction Failed."
        }), 500

if __name__ == "__main__":
    app.run(debug=True)