# Fitbit2Oscar CLI

## Overview

Fitbit2Oscar is a command-line interface (CLI) tool designed to convert Fitbit sleep and health data into a format compatible with the OSCAR CPAP reporting software. It supports multiple data sources, including Fitbit data exports from Google Takeout and Health Sync.

## Features

- Converts Fitbit sleep and vitals data to OSCAR-compatible format
- Supports both Google Takeout and Health Sync exports
- Allows filtering data by date range
- Logs detailed processing information with adjustable verbosity levels
- Plugin-based architecture for extensibility
- Supports JSON and CSV output formats

## Quickstart

### Dependencies

#### Python dependencies

The only third party dependencies for this project is Pydantic. Future 3rd-party plugins may have additional dependencies, as well as being dependencies themselves.

#### Environment dependencies

Fitbit2Oscar will run on all operating systems that support the standard Python interpreter, and requires Python 3.10+. A virtual environment is recommended. See installation for more information.

#### Fitbit Data dependencies

The Fitbit data must be exported with a supported exporter. Currently, the options are Google Takeout and the Health Sync app.

#### Google Takeout

1. Go to [https://takeout.google.com] and log into the Google Account used for your Fitbit.
2. Click "Deselect All" then check "Fitbit data" then click the button "Next step"
3. Chose data transfer type, whether to receive a download link in email or have the data sent directly to a cloud storage folder (Drive, Dropbox, OneDrive, or Box).
4. Chose download frequency, whether a single download or regular downloads every 2 months for a year.
5. Chose archive type (chose zip if Windows, gzip if Linux), and maximum archive size. Then click "Create export" button.
6. Wait. It could take a few minutes or a few hours.
7. Extract the archive to a directory that you will pass to Fitbit2Oscar.

#### Health Sync

Health Sync[https://healthsync.app/] is an app available on the Google Play store and Apple App Store that allows you to sync health data between various apps and also back up health data to your Google Drive account. It is a paid app with a 1 week free trial.

1. Install the app on your device.
2. Go to options ->  Connected Apps and connect your Fitbit account and Google Drive account.
3. In the main screen, enable the checkboxes for Sleep, Heart rate, and Oxygen saturation.
4. For each on it will ask you which data source you want to sync from. Select Fitbit and then tap "OK".
5. Chose the destination app to sync the data to. This should be Google Drive. Tap "OK" again.
6. A folder for each data type should arrive in your Google Drive account within a few minutes, with data files in each one. If you create a folder, such as "Health Sync" and move those folders into it, the files will be stored there instead.
7. Manually copy this folder to your local computer or use the Google Drive desktop app to allow your Google Drive account to be accessed locally.

### Installation

Clone the repository, navigate to the project directory, and create a virtual environment:

```sh
git clone https://github.com/your-repo/fitbit2oscar.git
cd fitbit2oscar
python -m venv .venv
```

Next, activate the virtual environment:

- MacOS/Linux:

```sh
source .venv/bin/activate
```

- Windows:

```dos
.venv\Scripts\activate
```

Next, install the dependencies:

```sh
pip install -r requirements.txt
```

Optionally, if you are familiar with uv, you can install Fitbit2Oscar as a command line tool with:

```sh
uv tool install git+https://github.com/ashrobertsdragon/fitbit2oscar.git
```

### Usage

Run the CLI tool with the following options:

```sh
python -m fitbit2oscar [input_source] -i/--fitbit_path <path> [options]
```

or with uv:

```sh
uv run fitbit2oscar [input_source] -i/--fitbit_path <path> [options]
```

If you installed Fitbit2Oscar as a uv tool, run the following instead:

```sh
uvx fitbit2oscar [input_source] -i/--fitbit_path <path> [options]
```

#### Arguments

- `input_source` (required): Source of Fitbit data. Options are:
  - `takeout` (default) - Google Takeout exports
  - `health_sync` - Health Sync exports (experimental)
  - Others to be added in the future
- `-i, --fitbit-path <path>` (required): Path to the Fitbit data directory

#### Options

- `-o, --export-path <path>`: Path to export the converted files (default: `export/`)
- `-s, --start-date <YYYY-M-D>`: Start date for data filtering (default: 2010-01-01)
- `-e, --end-date <YYYY-M-D>`: End date for data filtering (default: today's date)
- `-v, --verbose`: Enable verbose logging (INFO level)
- `-vv, --very-verbose`: Enable very verbose logging (DEBUG level)
- `-l, --logfile <filename.log>`: Log output to a file (requires verbose logging)
- `-f, --date-format <DAILY|WEEKLY|MONTHLY>`: Format for Health Sync date grouping (only applicable for `health_sync` input source)

#### Logging

Logging can be configured using the verbosity options. For logging to a file, a verbosity level must be set.

```sh
python -m fitbit2oscar takeout -v -l fitbit2oscar.log
```

#### Example Usage

Converting Fitbit data from Google Takeout:

```sh
python -m fitbit2oscar takeout -i /path/to/takeout -o /path/to/export
```

Converting Fitbit data from Health Sync with a custom date range:

```sh
python -m fitbit2oscar health_sync -i /path/to/health_sync -o /path/to/export -s 2024-01-01 -e 2024-02-01 -f DAILY
```

Exporting data in JSON format:

```sh
python -m fitbit2oscar takeout -i /path/to/takeout -o /path/to/export
```

### Error Handling

Common errors and their solutions:

- **Invalid date format**: Ensure dates follow the `YYYY-M-D` format.
- **Start date after end date**: Adjust the date range to be valid.
- **Missing input type**: Specify either `takeout` or `health_sync`.
- **Insufficient logging level for log file**: Use `-v` or `-vv` with `-l`.
- **FitbitConverterError**: A common exception class for all exceptions that occur during runtime including:
  - **FitbitConverterInputError**: An exception that occurs when there is an issue with the input.
  - **FitbitConverterDataError**: An exception that occurs when there is an issue with the data.

## License

This project is licensed under the MIT License.

## Contact

For issues or questions, please visit the project repository: [GitHub](https://github.com/your-repo/fitbit2oscar)

### TODO

- Automated updating of IANA and MS TZI databases.
- Test coverage.
- Documentation beyond docstrings and README.

### Contributing

Contributions are welcome! Please submit a pull request or open an issue for discussion.
