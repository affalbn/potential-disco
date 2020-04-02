#!/usr/bin/env python

import os
import sys
import requests
import mysql.connector as mysql
from dotenv import load_dotenv

# Load variable from .env file
load_dotenv()
# Global environment
db_plesk = os.getenv("DB_PLESK")
db_app = os.getenv("DB_APP")
server_list = os.getenv("SERVER_LIST").split(",")
api_token = os.getenv("API_TOKEN").split(",")

class MysqlConn:
    def connect():
        connect = mysql.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST")
        )
        return connect

class Build:
    def __init__(self):
        pass

    def create_db(self):
        connect = MysqlConn.connect()
        cursor = connect.cursor()

        sql = "CREATE DATABASE IF NOT EXISTS {0}".format(db_app)
        cursor.execute(sql)

        sql = """CREATE TABLE IF NOT EXISTS {0}.domains
        SELECT id,cr_date,name,displayName,parentDomainID
        FROM {1}.domains ORDER BY id ASC""".format(db_app,db_plesk)
        cursor.execute(sql)
        connect.close()

class DomProhibit:
    def __init__(self):
        pass

    def check_added_domain(self):
        connect = MysqlConn.connect()
        cursor = connect.cursor()

        sql = "SELECT id,name FROM {0}.domains WHERE `id` NOT IN (select id from {1}.domains)".format(db_plesk,db_app)
        cursor.execute(sql)

        new_domain_id = []
        for item in cursor:
            new_domain_id.append(item)

        connect.close()
        return new_domain_id

    def check_deleted_domain(self):
        connect = MysqlConn.connect()
        cursor = connect.cursor()

        sql = "SELECT id,name FROM {0}.domains WHERE `id` NOT IN (select id from {1}.domains)".format(db_app,db_plesk)
        cursor.execute(sql)

        removed_domain_id = []
        for item in cursor:
            removed_domain_id.append(item)

        connect.close()
        return removed_domain_id

    def add_domain_prohibit(self):
        connect = MysqlConn.connect()
        cursor = connect.cursor()

        new_domain = self.check_added_domain()
        if new_domain:
            # API request to add domain restricted
            for node, token in zip(server_list, api_token):
                header = {"X-API-KEY": token, "Accept": "application/json", "Content-Type": "application/json"}
                url = "https://{0}:8443/api/v2/cli/domain_restriction/call".format(node)
                for id, domain_name in new_domain:
                    param = {"params": ["--add","-name", domain_name]}
                    resp = requests.post(url, headers=header, json=param)
                    if resp.status_code != 200:
                        print("POST domain_restriction/call {0}".format(resp.status_code))

            # Insert added domain to database
            sql = """INSERT INTO {0}.domains
            SELECT id,cr_date,name,displayName,parentDomainID FROM {1}.domains
            WHERE `id` NOT IN (SELECT id FROM {2}.domains)
            """.format(db_app,db_plesk,db_app)
            cursor.execute(sql)
            connect.commit()
            connect.close()
            print("Check completed. New domain added.")
        else:
            print("Check completed. No new domain.")

    def remove_domain_prohibit(self):
        connect = MysqlConn.connect()
        cursor = connect.cursor()

        deleted_domain = self.check_deleted_domain()
        if deleted_domain:
            # Api request to remove domain prohibited
            for node, token in zip(server_list, api_token):
                header = {"X-API-KEY": token, "Accept": "application/json", "Content-Type": "application/json"}
                url = "https://{0}:8443/api/v2/cli/domain_restriction/call".format(node)
                for id, domain_name in deleted_domain:
                    param = {"params": ["--remove", "-name", domain_name]}
                    resp = requests.post(url, headers=header, json=param)
                    if resp.status_code != 200:
                        print("POST domain_restriction/call {0}".format(resp.status_code))

            # Delete old domain from database
            for id,domain_name in deleted_domain:
                sql = "DELETE FROM {0}.domains WHERE id={1}".format(db_app,id)
                cursor.execute(sql)
                connect.commit()
            connect.close()
            print("Check completed. Old domain removed.")
        else:
            print("Check completed. No old domain.")

def main(argv):
    usage = """Usage:
        --build  Initiate database
        --run    Check either there is/are new or old domain"""

    if argv:
        if "--build" in argv:
            print("Building DB.")
        elif "--run" in argv:
            print("Checking domain.")
        else:
            print(usage)
    else:
        print(usage)

if __name__ == '__main__':
    main(sys.argv[1:])
