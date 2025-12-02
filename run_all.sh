#!/bin/bash

# Script to execute in sequence all numbered files from 0 to 10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directory where the scripts are located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Success and failure counters
SUCCESS=0
FAILED=0

# Arrays to store execution details
declare -a STEP_NAMES
declare -a STEP_TIMES
declare -a STEP_STATUSES

# Output file for summary
OUTPUT_FILE="${SCRIPT_DIR}/execution_summary_$(date +%Y%m%d_%H%M%S).txt"

# Function to generate and save summary report
generate_summary() {
    local end_time=$(date +%s)
    local total_time=$((end_time - START_TIME))
    local hours=$((total_time / 3600))
    local minutes=$(((total_time % 3600) / 60))
    local seconds=$((total_time % 60))
    
    # Format total time string
    local total_time_str
    if [ $hours -gt 0 ]; then
        total_time_str="${hours}h ${minutes}m ${seconds}s"
    elif [ $minutes -gt 0 ]; then
        total_time_str="${minutes}m ${seconds}s"
    else
        total_time_str="${seconds}s"
    fi
    
    # Display summary on screen
    echo "=========================================="
    echo "Execution summary:"
    echo -e "${GREEN}Successes: $SUCCESS${NC}"
    echo -e "${RED}Failures: $FAILED${NC}"
    echo -e "Total execution time: ${total_time_str}"
    echo "=========================================="
    echo ""
    echo "Detailed execution log saved to: $OUTPUT_FILE"
    
    # Write detailed summary to file
    {
        echo "=========================================="
        echo "Execution Summary Report"
        echo "Generated: $(date)"
        echo "=========================================="
        echo ""
        echo "Overall Statistics:"
        echo "  Successes: $SUCCESS"
        echo "  Failures: $FAILED"
        echo "  Total execution time: ${total_time_str}"
        echo ""
        echo "=========================================="
        echo "Step-by-Step Execution Details:"
        echo "=========================================="
        echo ""
        
        for i in {0..10}; do
            if [ -n "${STEP_NAMES[$i]}" ]; then
                printf "[%2d] %-50s | Status: %-10s | Time: %s\n" "$i" "${STEP_NAMES[$i]}" "${STEP_STATUSES[$i]}" "${STEP_TIMES[$i]}"
            fi
        done
        
        echo ""
        echo "=========================================="
        echo "End of Report"
        echo "=========================================="
    } > "$OUTPUT_FILE"
}

# Start timing
START_TIME=$(date +%s)

echo "=========================================="
echo "Executing scripts in sequence (0-10)"
echo "=========================================="
echo ""

# Loop from 0 to 10
for i in {2..10}; do
    # Search for files that start with the number followed by underscore or without extension
    FILE=$(find "$SCRIPT_DIR" -maxdepth 1 -name "${i}_*.py" -o -name "${i}.py" | head -n 1)
    
    if [ -z "$FILE" ]; then
        echo -e "${YELLOW}[$i] File not found${NC}"
        STEP_NAMES[$i]="[${i}] File not found"
        STEP_TIMES[$i]="N/A"
        STEP_STATUSES[$i]="SKIPPED"
        continue
    fi
    
    FILENAME=$(basename "$FILE")
    echo -e "${YELLOW}[$i] Executing: $FILENAME${NC}"
    
    # Start timing for this step
    STEP_START=$(date +%s)
    
    # Execute the Python script
    if python3 "$FILE"; then
        STEP_END=$(date +%s)
        STEP_TIME=$((STEP_END - STEP_START))
        STEP_HOURS=$((STEP_TIME / 3600))
        STEP_MINUTES=$(((STEP_TIME % 3600) / 60))
        STEP_SECONDS=$((STEP_TIME % 60))
        
        # Format time string
        if [ $STEP_HOURS -gt 0 ]; then
            TIME_STR="${STEP_HOURS}h ${STEP_MINUTES}m ${STEP_SECONDS}s"
        elif [ $STEP_MINUTES -gt 0 ]; then
            TIME_STR="${STEP_MINUTES}m ${STEP_SECONDS}s"
        else
            TIME_STR="${STEP_SECONDS}s"
        fi
        
        echo -e "${GREEN}[$i] ✓ Success: $FILENAME (Time: ${TIME_STR})${NC}"
        STEP_NAMES[$i]="$FILENAME"
        STEP_TIMES[$i]="$TIME_STR"
        STEP_STATUSES[$i]="SUCCESS"
        ((SUCCESS++))
    else
        STEP_END=$(date +%s)
        STEP_TIME=$((STEP_END - STEP_START))
        STEP_HOURS=$((STEP_TIME / 3600))
        STEP_MINUTES=$(((STEP_TIME % 3600) / 60))
        STEP_SECONDS=$((STEP_TIME % 60))
        
        # Format time string
        if [ $STEP_HOURS -gt 0 ]; then
            TIME_STR="${STEP_HOURS}h ${STEP_MINUTES}m ${STEP_SECONDS}s"
        elif [ $STEP_MINUTES -gt 0 ]; then
            TIME_STR="${STEP_MINUTES}m ${STEP_SECONDS}s"
        else
            TIME_STR="${STEP_SECONDS}s"
        fi
        
        echo -e "${RED}[$i] ✗ Failed: $FILENAME (Time: ${TIME_STR})${NC}"
        STEP_NAMES[$i]="$FILENAME"
        STEP_TIMES[$i]="$TIME_STR"
        STEP_STATUSES[$i]="FAILED"
        ((FAILED++))
        echo -e "${RED}Stopping execution due to error.${NC}"
        generate_summary
        exit 1
    fi
    echo ""
done

# Generate and display summary
generate_summary

# Return exit code based on result
if [ $FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi

