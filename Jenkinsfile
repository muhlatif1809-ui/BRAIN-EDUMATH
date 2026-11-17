pipeline {
    agent any

    environment {
        CONTAINER_NAME = 'nivor-app-18'
        APP_PORT = '4006'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare Storage') {
            steps {
                sh '''
                    mkdir -p static/uploads backups
                    touch brain_edumath.db
                '''
            }
        }

        stage('Build & Deploy') {
            steps {
                sh '''
                    docker compose down --remove-orphans || true
                    docker compose build --no-cache
                    docker compose up -d
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    sleep 3
                    docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                '''
            }
        }
    }

    post {
        failure {
            sh 'docker logs --tail 50 ${CONTAINER_NAME} || true'
        }
    }
}
