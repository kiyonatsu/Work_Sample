namp_data_dir=$1

if [ -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]
then
  GOOGLE_APPLICATION_CREDENTIALS="/etc/namp/ims/gcp/datainfra_key.json"
  export GOOGLE_APPLICATION_CREDENTIALS
fi

if [ ! -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]; then
    echo "missing google credential file: GOOGLE_APPLICATION_CREDENTIALS" >&2
    exit 1
fi

if [ -z "${namp_data_dir}" ]
then
      echo "bash start_mon_service.sh <namp_data_dir>" >&2
      exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"/.. || exit 1
export PYTHONPATH=${PWD}
date_suffix=$(date +%Y%m%d_%H%M%S)
(python3 src/service/mon_service.py "${namp_data_dir}") 1>"${HOME}/logs/mon_service_${date_suffix}.out" 2>"${HOME}/logs/mon_service_${date_suffix}.log"
