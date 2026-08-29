#!/bin/bash
cd paper
pdflatex agentlens.tex
pdflatex agentlens.tex  # run twice for references
echo "Done. Check agentlens.pdf"
