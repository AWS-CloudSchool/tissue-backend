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

        stage('Update Helm Values') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: "${GIT_CREDENTIALS_ID}",
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    ),
                    string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                    string(credentialsId: 'cognito-client-secret', variable: 'COGNITO_CLIENT_SECRET'),
                    string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY'),
                    string(credentialsId: 'vidcap-api-key', variable: 'VIDCAP_API_KEY'),
                    string(credentialsId: 'langchain-api-key', variable: 'LANGCHAIN_API_KEY'),
                    string(credentialsId: 'youtube-api-key', variable: 'YOUTUBE_API_KEY')
                ]) {
                    sh """
                    git checkout main
                    git config user.name "Jenkins CI"
                    git config user.email "jenkins@yourcompany.com"
                    
                    git pull --rebase origin main
                    
                    # 이미지 태그 업데이트
                    sed -i 's|image: .*|image: ${ECR_REPO}:${IMAGE_TAG}|' manifests/deployment.yaml
                    
                    # 환경 변수 섹션 생성
                    cat > temp_env_section.yaml << 'EOF'
          env:
            - name: DB_HOST
              value: "tissu-test-database.c7oqui4icou3.us-west-2.rds.amazonaws.com"
            - name: DB_PORT
              value: "3306"
            - name: DB_USER
              value: "admin"
            - name: DB_PASSWORD
              value: "${DB_PASSWORD}"
            - name: DB_NAME
              value: "tissue"
            - name: COGNITO_USER_POOL_ID
              value: "us-west-2_vsGsSoTJe"
            - name: COGNITO_CLIENT_ID
              value: "6rqobnfsf0lnfen24me10j7d2v"
            - name: COGNITO_CLIENT_SECRET
              value: "${COGNITO_CLIENT_SECRET}"
            - name: AWS_ACCESS_KEY_ID
              value: "${AWS_ACCESS_KEY_ID}"
            - name: AWS_SECRET_ACCESS_KEY
              value: "${AWS_SECRET_ACCESS_KEY}"
            - name: AWS_REGION
              value: "us-west-2"
            - name: AWS_S3_BUCKET
              value: "s3-aws8"
            - name: YOUTUBE_LAMBDA_NAME
              value: "aws8"
            - name: BEDROCK_KB_ID
              value: "8LPGWWQYCM"
            - name: BEDROCK_DS_ID
              value: "E33HDTF9XZ"
            - name: BEDROCK_MODEL_ID
              value: "anthropic.claude-3-5-sonnet-20241022-v2:0"
            - name: DYNAMODB_TABLE_NAME
              value: "LangGraphStates"
            - name: POLLY_VOICE_ID
              value: "Seoyeon"
            - name: VIDCAP_API_KEY
              value: "${VIDCAP_API_KEY}"
            - name: LANGCHAIN_API_KEY
              value: "${LANGCHAIN_API_KEY}"
            - name: LANGCHAIN_ENDPOINT
              value: "https://api.smith.langchain.com"
            - name: LANGCHAIN_PROJECT
              value: "Youtube-summarizer"
            - name: LANGCHAIN_TRACING_V2
              value: "true"
            - name: YOUTUBE_API_KEY
              value: "${YOUTUBE_API_KEY}"
EOF
                    
                    # 간단한 방법으로 env 섹션 추가
                    if grep -q "env:" manifests/deployment.yaml; then
                        echo "Environment variables already exist, updating..."
                        # env: 라인부터 다음 섹션까지 삭제하고 새로 추가
                        sed -i '/env:/,/^[[:space:]]*[^[:space:]-]/d' manifests/deployment.yaml
                        sed -i '/image: /r temp_env_section.yaml' manifests/deployment.yaml
                    else
                        echo "Adding environment variables..."
                        # image 라인 다음에 env 섹션 추가
                        sed -i '/image: /r temp_env_section.yaml' manifests/deployment.yaml
                    fi
                    
                    # 임시 파일 삭제
                    rm temp_env_section.yaml
                    
                    git add manifests/deployment.yaml
                    git commit -m "Update image tag to ${IMAGE_TAG} and add environment variables [skip ci]"
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
