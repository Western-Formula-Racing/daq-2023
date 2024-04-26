from influxdb_client import InfluxDBClient, Dialect
import csv 
import zipfile
import os
import mmap

from motec_conversion.data_log import DataLog
from motec_conversion.motec_log import MotecLog

class InfluxDataRetrieval:
    def __init__(self, url, token, org):
        self._influx_client = InfluxDBClient(url=url, token=token, org=org, timeout=45000)
        self._query_api = self._influx_client.query_api()

    def _writeToCsv(self, device_name: str, header: list[str], rows: dict[str, list]) -> str:
        with open(f'{device_name}.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in list(rows):
                r = [row]
                for dp in rows[row]:
                    r.append(dp)

                writer.writerow(r) # timestamp, value1, value2, ...

        return f'{device_name}.csv'

    def _generateZip(self, title: str, file_names: list[str]) -> str:
        if title == "no_data":
            return "no_data.zip"
            
        with zipfile.ZipFile(f'./static/{title}.zip', 'w') as zf:
            for file_name in file_names:
                zf.write(f'{file_name}')

            zf.close()
        
        return f'{title}.zip'

    def _deleteFiles(self, file_names: list[str]) -> None:
        for file_name in file_names:
            os.remove(file_name)

    # Return a tuple containing the last_time of measurement, and the file_names of all generated CSVs 
    def _generateAllDataPointsCSV(self, tag):
        # each MEASUREMENT (i.e., CAN device) will have an equal number of datapoints for all devices (CAN signals), 
        # because each datapoint represents a segment of a single CAN frame. On that CAN frame, there will always be values
        # for all other signals
        f = open(f'static/data.csv', 'w', newline='')
        records = self._query_api.query_stream(f'from(bucket: "RaceData") |> range(start: 0, stop: now()) |> filter(fn: (r) => r["session_hash"] == "{tag}") |> group(columns: ["_measurement"]) |> group(columns: ["_field"]) |> group(columns: ["_time"])')
        current_col = 1
        row = ""
        table_no = -1
        measurement_field_names_to_columns = {}
        for record in records:
            measurement_field_name = f'{record["_measurement"]}/{record["_field"]}'
            if table_no != record["table"]: # then we know we are on a new set of signals 
                if row != "":
                    f.write(row + "\n")
                    row = ""
                table_no = record.table # a "table" is a set of signals from one message
                row += f'{record["_time"]}' # change this into timestamp
                if measurement_field_name in measurement_field_names_to_columns:
                    current_col = 1
                    row += ',' * measurement_field_names_to_columns[measurement_field_name] # add offset
                    row += f'{record["_value"]}'
                    current_col += 1
                else:
                    measurement_field_names_to_columns[measurement_field_name] = current_col
                    row += ',' * current_col # add offset
                    row += f'{record["_value"]}'
                    current_col += 1
            else:
                if measurement_field_name in measurement_field_names_to_columns:
                    row += f',{record["_value"]}'
                else:
                    measurement_field_names_to_columns[measurement_field_name] = current_col
                    row += f',{record["_value"]}'
                current_col += 1
        
        f.close()
        
        # write the header in the beginning with memory mapping to avoid having to copy the entire file contents to memory 
        with open("static/data.csv", "r+b") as f:
            header = ("timestamp," + ','.join(list(measurement_field_names_to_columns.keys())) + "\n").encode("ascii")
            mm = mmap.mmap(f.fileno(), 0)
            existing = mm[:]
            mm.resize(len(existing) + len(header))
            mm[len(header):] = existing
            mm[:len(header)] = header
            mm.close()
        return 'data.csv'

    def writeAllDataPointsWithTagCSV(self, tag) -> str:
        name = self._generateAllDataPointsCSV(tag)
        return name

    def writeAllDataPointsWithTagMotec(self, tag) -> str: 
        last_time, file_names = self._generateAllDataPointsCSV(tag)
        i = 0
        for file_name in file_names:
            with open(file_name, "r") as f:
                lines = f.readlines()

            # Set the data log object
            data_log = DataLog()
            data_log.from_csv_log(lines)
            data_log.resample(20.0) # experimental value in Hz I think
            
            # Set metadata fields for the motec log object
            motec_log = MotecLog()
            motec_log.driver = "Maybe Samya?"
            motec_log.vehicle_id = "WFR24"
            motec_log.vehicle_weight = 0
            motec_log.vehicle_type = "FSAE"
            motec_log.vehicle_comment = "Built with Love"
            motec_log.venue_name = ""
            motec_log.event_name = ""
            motec_log.event_session = ""
            motec_log.long_comment = ""
            motec_log.short_comment = ""

            motec_log.initialize()
            motec_log.add_all_channels(data_log)
            
            # Save the motec log
            ld_filename = os.path.join(file_name[0:-3] + "ld") # "./blahblah.csv" -> "./blahblah.ld"
            file_names[i] = ld_filename
            i += 1
            motec_log.write(ld_filename)

        zip_name = self._generateZip(last_time, file_names)
        self._deleteFiles(file_names)
        return zip_name
