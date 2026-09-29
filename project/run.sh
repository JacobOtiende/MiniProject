#!/bin/bash
# MyAgent convenience runner - Linux/Mac bash script
# Usage: ./run triage | rundown | achievements | review

show_help() {
    echo "MyAgent - School Operations Assistant"
    echo ""
    echo "Usage:"
    echo "  ./run triage          - Process new school emails"
    echo "  ./run rundown         - Daily briefing (calendar + email)"
    echo "  ./run achievements    - Summary of completed tasks"
    echo "  ./run review          - Rundown + approval review"
    echo "  ./run help            - Show this message"
    echo ""
}

if [ $# -eq 0 ] || [ "$1" == "help" ]; then
    show_help
    exit 0
fi

case "$1" in
    triage)
        python main.py triage
        ;;
    rundown)
        python main.py rundown
        ;;
    achievements)
        python main.py achievements
        ;;
    review)
        python main.py rundown --review
        ;;
    *)
        echo "Unknown command: $1"
        echo "Valid commands: triage, rundown, achievements, review, help"
        exit 1
        ;;
esac
