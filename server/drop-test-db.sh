#!/bin/bash

sudo -u postgres psql -c \
  "DROP DATABASE machination_tests"
  sudo -u postgres psql -c \
  "DROP ROLE machination_tests"
  
