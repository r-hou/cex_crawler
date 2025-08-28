#!/usr/bin/env bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate

cd /root/cex_crawler
python main.py >> log.log
