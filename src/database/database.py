import mysql.connector as mysql
import mysql.connector.errors as mysql_err
from mysql.connector import errorcode
from collections.abc import Iterable

from error_handling.error_handler import ErrorHandler


class Database:
    def __init__(self, user, password, database="green_configurator", host="intelli001.medien.uni-weimar.de",
                 port=3306):
        self.connection = None
        self.cursor = None

        try:
            print("[DB] Connect to DB on " + host)
            self.connection = mysql.connect(
                user=user,
                password=password,
                database=database,
                host=host,
                port=port
            )

            self.cursor = self.connection.cursor()

        except mysql_err.Error as err:
            ErrorHandler.handle("DB", "Can't connect to " + host + ":" + str(port), err, terminate=True)

    def __execute_query__(self, statement, parameter=None):
        try:
            self.cursor.execute(statement, parameter)
        except mysql_err.Error as err:
            if err.errno == errorcode.ER_BAD_TABLE_ERROR:
                ErrorHandler.handle("DB", "Bad table", err)
            elif err.errno == errorcode.ER_BAD_FIELD_ERROR:
                ErrorHandler.handle("DB", "Bad field", err)
            elif err.errno == errorcode.ER_DUP_ENTRY:
                ErrorHandler.handle("DB", "Duplicate entry", err)
            else:
                ErrorHandler.handle("DB", "Unhandled exception occurred", err)

    def contains_value(self, table, field, value, is_json_type=False):
        if is_json_type:
            statement = "SELECT EXISTS(SELECT * FROM {tbl} WHERE JSON_CONTAINS({fld}, %(value)s)) as existence;".format(
                tbl=table,
                fld=field)
        else:
            statement = "SELECT EXISTS(SELECT * FROM {tbl} WHERE {fld} = %(value)s) as existence;".format(tbl=table,
                                                                                                          fld=field)
        self.__execute_query__(statement, parameter={"value": value})
        res = self.cursor.fetchone()[0]

        return res == 1

    def get_free_index(self, table):
        statement = "SELECT MAX(id) FROM {tbl};".format(tbl=table)

        self.__execute_query__(statement)
        res = self.cursor.fetchone()[0]

        if res is None:
            res = -1

        return res + 1

    def get_indices_of(self, table, fields, values, conjunction="AND"):
        if isinstance(fields, list):
            clause = (" " + conjunction + " ").join(["{} = {}"] * len(fields))
            pairs = list(zip(fields, values))
            ins = []
            for pair in pairs:
                ins.append(pair[0])
                ins.append(pair[1])

            clause = clause.format(*ins)

            statement = ("SELECT id FROM {tbl} WHERE "+clause + ";").format(tbl=table)
            parameter = None

        else:
            statement = "SELECT id FROM {tbl} WHERE {field} = %(value)s;".format(tbl=table, field=fields)
            parameter = {"value": values}

        self.__execute_query__(statement, parameter=parameter)
        res = [x[0] for x in self.cursor.fetchall()]

        return res

    def insert_data(self, table, data, fields=None):
        if len(data) == 0:
            return None

        if isinstance(data[0], list):
            values = ""
            for insertion in data:
                values += "(\"" + ("\", \"".join(insertion)) + "\"), "

            values = values.strip(", ")

            if fields is not None:
                fields = ", ".join(fields)
                statement = ("INSERT INTO {tbl} ({flds}) VALUES " + values + ";").format(tbl=table, flds=fields)
            else:
                statement = ("INSERT INTO {tbl} VALUES " + values + ";").format(tbl=table)

            self.__execute_query__(statement)
        else:
            values = ", ".join(["%s"] * len(data))

            if fields is None:
                statement = "INSERT INTO {tbl} VALUES ({val});".format(tbl=table, val=values)
            else:
                fields = ", ".join(fields)
                statement = "INSERT INTO {tbl} ({flds}) VALUES ({val});".format(tbl=table, flds=fields, val=values)

            self.__execute_query__(statement, parameter=data)

        self.connection.commit()

        self.__execute_query__("SELECT LAST_INSERT_ID();")
        return self.cursor.fetchone()[0]

    def get_data(self, table, fields=None, condition=None):
        fields_sql = "*"

        if fields is not None:
            fields_sql = ", ".join(fields)

        where_clause = ""
        if condition is not None:
            where_clause = "WHERE " + condition

        statement = "SELECT {flds} FROM {tbl} {where};".format(flds=fields_sql, tbl=table, where=where_clause)

        self.__execute_query__(statement)

        results = []
        for row in self.cursor.fetchall():
            results.append(row)

        return results

    def execute(self, sql, result_set=True):
        self.__execute_query__(sql)

        if result_set:
            results = []
            for row in self.cursor.fetchall():
                results.append(row)

            return results

        return None

    def close(self):
        self.cursor.close()
        self.connection.close()
