#!/bin/bash

source activate gc_energy_metering
python run.py -u green_admin -p SaveTheWorld
conda deactivate
