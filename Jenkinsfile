pipeline {
    agent {
        label 'jenkins-jenkins-agent'
    }

    environment {
        // Jenkins Credentials에서 가져올 환경 변수들
        AWS_REGION = "${env.AWS_REGION ?: 'us-west-2'}"
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        ECR_REPOSITORY = credentials('ecr-repository-name')
        ECR_REPO = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
        IMAGE_TAG = "build-${BUILD_NUMBER}"
        GIT_REPO = "https://github.com/AWS-CloudSchool/tissue-backend"
        GIT_CREDENTIALS_ID = "${env.GIT_CREDENTIALS_ID ?: 'git_cre'}"
        AWS_CREDENTIALS_ID = "${env.AWS_CREDENTIALS_ID ?: 'aws_cre'}"
        
        // Application 환경 변수들
        // Database 설정
        DB_HOST = "tissu-test-database.c7oqui4icou3.us-west-2.rds.amazonaws.com"
        DB_PORT = "3306"
        DB_USER = "admin"
        DB_PASSWORD = credentials('db-password')
        DB_NAME = "tissue"
        
        COGNITO_USER_POOL_ID = "us-west-2_vsGsSoTJe"
        COGNITO_CLIENT_ID = "6rqobnfsf0lnfen24me10j7d2v"
        COGNITO_CLIENT_SECRET = credentials('cognito-client-secret')
        
        AWS_ACCESS_KEY_ID = credentials('aws-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('aws-secret-access-key')
        AWS_S3_BUCKET = "s3-aws8"
        
        YOUTUBE_LAMBDA_NAME = "aws8"
        BEDROCK_KB_ID = "8LPGWWQYCM"
        BEDROCK_DS_ID = "E33HDTF9XZ"
        BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        DYNAMODB_TABLE_NAME = "LangGraphStates"
        POLLY_VOICE_ID = "Seoyeon"
        
        VIDCAP_API_KEY = credentials('vidcap-api-key')
        
        LANGCHAIN_API_KEY = credentials('langchain-api-key')
        LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
        LANGCHAIN_PROJECT = "Youtube-summarizer"
        LANGCHAIN_TRACING_V2 = "true"
        
        YOUTUBE_API_KEY = credentials('youtube-api-key')
    }

    stages {
        stage('Check Skip CI') {
            steps {
                script {
                    def lastCommitMessage = sh(
                        script: 'git log -1 --pretty=%B',
                        returnStdout: true
                    ).trim()
                    
                    if (lastCommitMessage.contains('[skip ci]') || 
                        lastCommitMessage.contains('[ci skip]')) {
                        currentBuild.result = 'ABORTED'
                        error('Skipping CI due to [skip ci] in commit message')
                    }
                }
            }
        }

        stage('Clone Repository') {
            steps {
                checkout([$class: 'GitSCM',
                    branches: [[name: '*/main']],
                    userRemoteConfigs: [[
                        url: "${GIT_REPO}",
                        credentialsId: "${GIT_CREDENTIALS_ID}"
                    ]]
                ])
            }
        }

        stage('Docker Build') {
            steps {
                container('docker') {
                    sh """
                        echo "Starting Docker daemon..."
                        dockerd --host=unix:///var/run/docker.sock &
                        
                        for i in \$(seq 1 15); do
                            if docker info >/dev/null 2>&1; then
                                echo "Docker daemon is ready!"
                                break
                            fi
                            echo "Waiting... (\$i/15)"
                            sleep 2
                        done
                        
                        docker build -t ${ECR_REPO}:${IMAGE_TAG} .
                        docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_REPO}:latest
                    """
                }
            }
        }

        stage('Push to ECR') {
            steps {
                container('docker') {
                    withCredentials([[ 
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: "${AWS_CREDENTIALS_ID}"
                    ]]) {
                        sh """
                        apk add --no-cache aws-cli
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}
                        docker push ${ECR_REPO}:${IMAGE_TAG}
                        docker push ${ECR_REPO}:latest
                        docker image rm ${ECR_REPO}:${IMAGE_TAG}
                        docker image rm ${ECR_REPO}:latest
                        """
                    }
                }
            }
        }

        stage('Update Kubernetes Deployment') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: "${GIT_CREDENTIALS_ID}",
                    usernameVariable: 'GIT_USERNAME',
                    passwordVariable: 'GIT_PASSWORD'
                )]) {
                    sh """
                    git checkout main
                    git config user.name "Jenkins CI"
                    git config user.email "jenkins@yourcompany.com"
                    
                    git pull --rebase origin main
                    
                    # Kubernetes deployment.yaml 업데이트
                    sed -i 's|image: .*|image: ${ECR_REPO}:${IMAGE_TAG}|' tissue-backend-all.yaml
                    
                    # 환경 변수 섹션 업데이트
                    cat > temp_env.yaml << 'EOF'
          env:
            - name: DB_HOST
              value: "${DB_HOST}"
            - name: DB_PORT
              value: "${DB_PORT}"
            - name: DB_USER
              value: "${DB_USER}"
            - name: DB_PASSWORD
              value: "${DB_PASSWORD}"
            - name: DB_NAME
              value: "${DB_NAME}"
            - name: COGNITO_USER_POOL_ID
              value: "${COGNITO_USER_POOL_ID}"
            - name: COGNITO_CLIENT_ID
              value: "${COGNITO_CLIENT_ID}"
            - name: COGNITO_CLIENT_SECRET
              value: "${COGNITO_CLIENT_SECRET}"
            - name: AWS_ACCESS_KEY_ID
              value: "${AWS_ACCESS_KEY_ID}"
            - name: AWS_SECRET_ACCESS_KEY
              value: "${AWS_SECRET_ACCESS_KEY}"
            - name: AWS_REGION
              value: "${AWS_REGION}"
            - name: AWS_S3_BUCKET
              value: "${AWS_S3_BUCKET}"
            - name: YOUTUBE_LAMBDA_NAME
              value: "${YOUTUBE_LAMBDA_NAME}"
            - name: BEDROCK_KB_ID
              value: "${BEDROCK_KB_ID}"
            - name: BEDROCK_DS_ID
              value: "${BEDROCK_DS_ID}"
            - name: BEDROCK_MODEL_ID
              value: "${BEDROCK_MODEL_ID}"
            - name: DYNAMODB_TABLE_NAME
              value: "${DYNAMODB_TABLE_NAME}"
            - name: POLLY_VOICE_ID
              value: "${POLLY_VOICE_ID}"
            - name: VIDCAP_API_KEY
              value: "${VIDCAP_API_KEY}"
            - name: LANGCHAIN_API_KEY
              value: "${LANGCHAIN_API_KEY}"
            - name: LANGCHAIN_ENDPOINT
              value: "${LANGCHAIN_ENDPOINT}"
            - name: LANGCHAIN_PROJECT
              value: "${LANGCHAIN_PROJECT}"
            - name: LANGCHAIN_TRACING_V2
              value: "${LANGCHAIN_TRACING_V2}"
            - name: YOUTUBE_API_KEY
              value: "${YOUTUBE_API_KEY}"
EOF
                    
                    # 기존 env 섹션을 새로운 것으로 교체
                    python3 -c "
import re
with open('tissue-backend-all.yaml', 'r') as f:
    content = f.read()

with open('temp_env.yaml', 'r') as f:
    new_env = f.read()

# env 섹션 교체
pattern = r'(\\s+)env:\\s*\\n(\\s*-\\s*name:.*?\\n\\s*value:.*?\\n)*'
replacement = new_env
content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

with open('tissue-backend-all.yaml', 'w') as f:
    f.write(content)
"
                    
                    rm temp_env.yaml
                    
                    git add tissue-backend-all.yaml
                    git commit -m "Update image tag to ${IMAGE_TAG} and environment variables [skip ci]"
                    git push https://\${GIT_USERNAME}:\${GIT_PASSWORD}@github.com/AWS-CloudSchool/tissue-backend.git main
                    """
                }
            }
        }
    }

    post {
        success {
            echo "✅ 파이프라인 성공! ArgoCD가 자동으로 배포를 시작합니다."
        }
        failure {
            echo "❌ 파이프라인 실패"
        }
    }
}
