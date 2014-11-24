#!/bin/bash

sudo -u postgres psql -c \
  "CREATE ROLE machination_tests WITH LOGIN PASSWORD 'machination_tests'"
sudo -u postgres psql -c \
  "CREATE DATABASE machination_tests WITH OWNER machination_tests"
