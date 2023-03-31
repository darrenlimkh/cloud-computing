import psycopg2 
from psycopg2 import sql
import datetime

class RDSdatabase:
    def __init__(self, masterUserName, masterPassword, rdsHostName, rdsDBName, rdsPort):
        self.masterEngine = psycopg2.connect(
            database = rdsDBName, #postgres
            user=masterUserName, #"masteruser"
            password=masterPassword, #"hishmaster123"
            host=rdsHostName, #"hish-db-01.cfwyts8tlkjs.us-east-1.rds.amazonaws.com"
            port=rdsPort #5432
        )

        self.masterCursor = self.masterEngine.cursor()
        self.masterEngine.autocommit = True
        self.databaseName = rdsDBName
        self.hostName = rdsHostName
        self.portNum = rdsPort

    def initialConfig(self): #run when starting app
        #create tables for organisation and user details
        sqlQuery = sql.SQL("""
        CREATE TABLE userDetails (
        userName VARCHAR (50) PRIMARY KEY,
        password VARCHAR (50) NOT NULL,
        organisationName VARCHAR (100) NOT NULL
        );

        CREATE TABLE joint_table (
        isLeftBreast BOOLEAN NOT NULL,
        isImplant BOOLEAN NOT NULL,
        density VARCHAR(1) NOT NULL,
        remarks VARCHAR(100) NOT NULL,
        concavityMean FLOAT NOT NULL,
        concavitySE FLOAT NOT NULL,
        areaMean FLOAT NOT NULL,
        areaSE FLOAT NOT NULL,
        areaWorst FLOAT NOT NULL,
        symmetryMean FLOAT NOT NULL,
        textureMean FLOAT NOT NULL,
        diagnosis VARCHAR (100) NOT NULL,
        dateOfClosure TIMESTAMP NOT NULL
        );
        """)

        self.masterCursor.execute(sqlQuery)

    def mapOrganisationNameToTableName(self, organisationName):
        return f"{organisationName}_Data"

    def createNewOrganisation(self, organisationName):
        newTableName = self.mapOrganisationNameToTableName(organisationName)
        colSeqName = f"{newTableName}_patientid_seq"

        #TO-DO: update schema
        sqlQuery = sql.SQL("""
        CREATE ROLE {role};
        GRANT CONNECT ON DATABASE {dbName} TO {role};

        CREATE TABLE {table} (
        patientid SERIAL PRIMARY KEY,
        firstName VARCHAR (50) NOT NULL,
        lastName VARCHAR (50) NOT NULL,
        dateOfBirth TIMESTAMP NOT NULL,
        dateOfService TIMESTAMP NOT NULL, 
        areaCode INT NOT NULL,
        phoneNumber INT NOT NULL,
        isLeftBreast BOOLEAN NOT NULL,
        isImplant BOOLEAN NOT NULL,
        density VARCHAR(1) NOT NULL,
        remarks VARCHAR(100) NOT NULL,
        concavityMean FLOAT NOT NULL,
        concavitySE FLOAT NOT NULL,
        areaMean FLOAT NOT NULL,
        areaSE FLOAT NOT NULL,
        areaWorst FLOAT NOT NULL,
        symmetryMean FLOAT NOT NULL,
        textureMean FLOAT NOT NULL,
        diagnosis VARCHAR (100),
        dateOfClosure TIMESTAMP
        );
        
        GRANT INSERT, UPDATE ON TABLE joint_table TO {role};
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO {role};
        GRANT USAGE, SELECT ON SEQUENCE {colSeq} TO {role};
        """).format(
                role=sql.Identifier(organisationName),
                table=sql.Identifier(newTableName),
                dbName=sql.Identifier(self.databaseName),
                colSeq=sql.Identifier(colSeqName)
        )
        self.masterCursor.execute(sqlQuery)

    def createNewUser(self, userName, userPassword, organisationName):

        sqlQuery = sql.SQL("""
        CREATE USER {user} WITH ENCRYPTED PASSWORD %s;
        GRANT {organisatiolRole} TO {user};
        INSERT INTO userDetails VALUES (%s, %s, %s);
        """).format(
            user=sql.Identifier(userName),
            organisatiolRole=sql.Identifier(organisationName)
        )
        self.masterCursor.execute(sqlQuery, (userPassword,userName,userPassword,organisationName))

    #TO-DO: not sure if handling multiple users will cause problem
    def userSignIn(self, userName, userPassword):
        userEngine = psycopg2.connect(
            database=self.databaseName,
            user=userName,
            password=userPassword,
            host=self.hostName,
            port=self.portNum
        )

        userCursor = userEngine.cursor()
        userEngine.autocommit = True
        return userEngine, userCursor

    def userViewTable(self, userName, userPassword, organisationName):
        currentUserEngine, currentUserCursor = self.userSignIn(userName, userPassword)
        userTableName = self.mapOrganisationNameToTableName(organisationName)
        currentUserCursor.execute(sql.SQL("SELECT * FROM {table};").format(table=sql.Identifier(userTableName)))
        return currentUserCursor.fetchall(), currentUserEngine, currentUserCursor
    
    def addPatientData(self,userName, userPassword, organisationName, firstName,lastName,DOB,date_of_service,area_code,phoneNum,is_left_breast,is_implant,
                       density,remarks,concavity_mean,concavity_SE,area_mean,area_SE,area_worst,symmetry_mean,
                       texture_mean,diagnosis=None,date_of_closure=None):
        currentUserEngine, currentUserCursor = self.userSignIn(userName, userPassword)
        userTableName = self.mapOrganisationNameToTableName(organisationName)

        #adding the compulsory attributes first 
        sqlQuery = sql.SQL("""
        INSERT INTO {table} (firstName,lastName,dateOfBirth,dateOfService,areaCode,phoneNumber,isLeftBreast,isImplant,density,remarks,concavityMean,concavitySE,areaMean,areaSE,areaWorst,symmetryMean,textureMean,diagnosis,date_of_closure) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        SELECT * FROM {table};
        """).format(table=sql.Identifier(userTableName))
        currentUserCursor.execute(sqlQuery, (firstName,lastName,DOB,date_of_service,area_code,phoneNum,is_left_breast,is_implant,density,remarks,concavity_mean,concavity_SE,area_mean,area_SE,area_worst,symmetry_mean,texture_mean,diagnosis,date_of_closure))
        return currentUserCursor.fetchall(), currentUserEngine, currentUserCursor
    
    def saveCloseCaseInDatabase(self, userName, userPassword, is_left_breast,is_implant,
                       density,remarks,concavity_mean,concavity_SE,area_mean,area_SE,area_worst,symmetry_mean,
                       texture_mean,diagnosis,date_of_closure):
        currentUserEngine, currentUserCursor = self.userSignIn(userName, userPassword)
        sqlQuery = sql.SQL("""
        INSERT INTO joint_table (isLeftBreast,isImplant,density,remarks,concavityMean,concavitySE,areaMean,areaSE,areaWorst,symmetryMean,textureMean,diagnosis,dateOfClosure) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        """)
        currentUserCursor.execute(sqlQuery, (is_left_breast,is_implant,density,remarks,concavity_mean,concavity_SE,area_mean,area_SE,area_worst,symmetry_mean,texture_mean,diagnosis,date_of_closure))
        return currentUserEngine, currentUserCursor

    def removeUser(self, userName):
        self.masterCursor.execute(sql.SQL("DROP USER IF EXISTS {user};").format(user=sql.Identifier(userName)))

    def closeUser(self, userEngine):
        userEngine.close()

    def closeMaster(self):
        self.masterEngine.close()