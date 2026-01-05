#!/usr/bin/env bash

# set -eo pipefail

# $1: dev or master
# $2: router or coordinator
# $3: ttyUSB port number

#################################
# Constants / global variables
#################################

# Colours

RED='\033[0;31m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

# Logging
LOGLEVEL='INFO'
QUIET=0 # verbose by default
LOGTOFILE=1 # Do not log to file by default
LOGDIR="."
LOGFILE="sonoff_flashing.log"

# App
TMP_PATH="./tmp"
BRANCH="master"
ZIGBEE_TYPE="coordinator"
FLASH=1

URL_BOOTLOADER="https://github.com/JelmerT/cc2538-bsl/raw/master/cc2538-bsl.py"
URL_FIRMWARE_COORDINATOR="https://github.com/Koenkk/Z-Stack-firmware/raw/master/coordinator/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_coordinator_20230507.zip"
URL_FIRMWARE_COORDINATOR_DEV="https://github.com/Koenkk/Z-Stack-firmware/raw/develop/coordinator/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_coordinator_20220507.zip"
URL_FIRMWARE_ROUTER="https://github.com/Koenkk/Z-Stack-firmware/raw/master/router/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_router_20220219.zip"
URL_FIRMWARE_ROUTER_DEV="https://github.com/Koenkk/Z-Stack-firmware/raw/develop/router/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_router_20220125.zip"

#################################
# Functions
#################################

# Logging functions
function _log {
  if [ $QUIET -eq 0 ]; then
    echo -e `date "+%Y/%m/%d %H:%M:%S"`" $1"
  fi

  if [ $LOGTOFILE -eq 0 ]; then
    echo `date "+%Y/%m/%d %H:%M:%S"`" $1" >> $LOGDIR/$LOGFILE
  fi
}

function log_debug {
  if [[ "$LOGLEVEL" =~ ^(DEBUG)$ ]]; then
    _log "DEBUG $1"
  fi
}

function log_info {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO)$ ]]; then
    _log "INFO $1"
  fi
}

function log_warn {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO|WARN)$ ]]; then
    _log "${ORANGE}WARN${NC} $1"
  fi
}

function log_error {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO|WARN|ERROR)$ ]]; then
    _log "${RED}ERROR${NC} $1"
  fi
}



#################################
# Main
#################################

# Get input parameters
while [[ "$1" != "" ]]; do
  case $1 in
      -l | --logfile )        shift
                              LOGFILE=$1
                              ;;
      -L | --loglevel )       shift
                              LOGLEVEL=$1
                              ;;
      -Q | --quiet )          shift
                              QUIET=1
                              ;;
      -h | --help )           show_usage
                              exit
                              ;;
      --FLASH )               shift
                              FLASH=0
                              ;;
      * )                     show_usage
                              exit 1
  esac
  shift
done

main () {
    if [ $1 -ne 3 ]
       then
          show_usage
       else
          shift
          check_if_sonoff
          prepare_python
          prepare_tmp_dir
          download_serial_bootloader
          download_firmware $1 $2
          flash_firmware $1 $2 $3
          cleanup
    fi
}

# Check if the sonoff usb zigbee 3.0 stick is connected
check_if_sonoff () {
    usb=$(ls -Alhr /dev/serial/by-id 2>/dev/null | tr '[:upper:]' '[:lower:]')

    if [ "$usb" != "${usb/sonoff}" ]; then
       log_info "USB has Sonoff connected"
    else
       log_error "USB has NO Sonoff connected, exiting."
       exit 1
    fi
}

prepare_tmp_dir() {
    rm -rf $TMP_PATH
    mkdir -p $TMP_PATH
}

download_serial_bootloader () {
    # python script that communicates with the boot loader of the
    # Texas Instruments CC2538, CC26xx and CC13xx SoCs (System on Chips)
    # https://github.com/JelmerT/cc2538-bsl

    cd $TMP_PATH
    wget $URL_BOOTLOADER
    if [[ $? -ne 0 ]]; then
      log_error "Download of bootloader failed."
      exit 1;
    fi
}

download_firmware () {
    # https://github.com/Koenkk/Z-Stack-firmware
    # No attempt is made to use github api to download latest versions.
    # Urls will need to be edited to point to correct files as updates
    # are posted to github.

    if [ $1 == "master" ]; then
      cd $TMP_PATH
      mkdir master
      cd master

      if [ $2 == "coordinator" ]; then
        # wget https://github.com/Koenkk/Z-Stack-firmware/raw/master/coordinator/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_coordinator_20220219.zip
	      wget https://github.com/Koenkk/Z-Stack-firmware/raw/master/coordinator/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_coordinator_20230507.zip

        if [[ $? -ne 0 ]]; then
          log_error "wget $1 coordinator failed"
          exit 1;
        fi
      fi

      if [ $2 == "router" ]; then
        wget https://github.com/Koenkk/Z-Stack-firmware/raw/master/router/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_router_20220219.zip

        if [[ $? -ne 0 ]]; then
          log_error "wget $1 router failed"
          exit 1;
        fi
      fi

      for f in *.zip; do unzip $f; done
    fi

    if [ $1 == "dev" ]; then
      cd $TMP_PATH
      mkdir dev
      cd dev

      # Dev branch coordinator as of 5/11/22
      if [ $2 == "coordinator" ]; then
        wget https://github.com/Koenkk/Z-Stack-firmware/raw/develop/coordinator/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_coordinator_20220507.zip

        if [[ $? -ne 0 ]]; then
          log_error "wget $1 coordinator failed"
          exit 1;
        fi
      fi

      if [ $2 == "router" ]; then
        wget https://github.com/Koenkk/Z-Stack-firmware/raw/develop/router/Z-Stack_3.x.0/bin/CC1352P2_CC2652P_launchpad_router_20220125.zip

        if [[ $? -ne 0 ]]; then
          log_error "wget $1 router failed"
          exit 1;
        fi
      fi

      for f in *.zip; do unzip $f; done
    fi
}

flash_firmware () {
    # for more options see: https://github.com/JelmerT/cc2538-bsl#cc26xx-and-cc13xx
    python $TMP_PATH/cc2538-bsl.py -evw -p $3 --bootloader-sonoff-usb $TMP_PATH/$1/*$2*.hex
}

cleanup () {
    rm -rf $TMP_PATH
}

show_usage() {
    # $1: dev or master
    # $2: router or coordinator
    # $3: ttyUSB port number
    echo
    echo "Usage: $0 [branch] [type] [usb port number]"
    echo
    echo "branch:  master or dev"
    echo "type:    coordinator or router"
    echo "port:    ttyUSB port number"
    echo
    echo "Note that dev of router may not be available at all"
    echo "Example: /ttyUSB0 --> 0"
    echo
    echo USB dongles found:
    echo $(ls -Alhr /dev/serial/by-id | awk '{print $9, $10, $11}')
    echo
}

prepare_python () {
    # dependencies needed for https://github.com/JelmerT/cc2538-bsl
    log_info "Check python dependencies"
    dep_array=("pyserial" "intelhex" "python-magic")
    pip_array=( $(pip list | grep -v "^Package *Version$" | grep -v "^-*$" | cut -d ' ' -f 1) )

    for dep in ${dep_array[@]}; do
       echo "${pip_array[@]}" | grep -q "$dep" &&  \
          log_info "Already installed $dep" || \
          pip install $dep
    done
}

main $# $1 $2 $3
