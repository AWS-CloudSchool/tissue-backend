pipeline {
    agent {
        label 'jenkins-jenkins-agent'
    }

    environment {
        // Jenkins Credentials에서  가져올 환경 변수들!!
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
                    # 실제 이미지 경로로 업데이트
                    sed -i 's|image: .*|image: ${ECR_REPO}:${IMAGE_TAG}|' manifests/deployment.yaml
                    git add manifests/deployment.yaml
                    git commit -m "Update image tag to ${IMAGE_TAG} [skip ci]"
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