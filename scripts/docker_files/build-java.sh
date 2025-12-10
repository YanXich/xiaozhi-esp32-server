#!/bin/bash
echo "Cleaning and building Java project..."
mvn clean package -Dmaven.test.skip=true

echo "Build complete! JAR file is in /app/target/"
