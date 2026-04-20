pipeline {
    agent {
        // Runs on the self-hosted K3s runner — same as other pipelines
        label 'self-hosted'
    }

    environment {
        // DockerHub image name
        IMAGE_NAME    = "gadiyadekho7/upload-portal"
        // Git commit SHA for image tag — no 'latest' tag ever
        IMAGE_TAG     = "${GIT_COMMIT[0..7]}"
        // K8s namespace
        NAMESPACE     = "tools"
        // K8s deployment name
        DEPLOYMENT    = "upload-portal"
        // Container name inside the pod
        CONTAINER     = "upload-portal"
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Building commit: ${GIT_COMMIT}"
                echo "Branch: ${GIT_BRANCH}"
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building image: ${IMAGE_NAME}:${IMAGE_TAG}"
                    sh """
                        docker build \
                            -t ${IMAGE_NAME}:${IMAGE_TAG} \
                            -t ${IMAGE_NAME}:latest \
                            .
                    """
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                script {
                    withCredentials([usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh """
                            echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
                            docker push ${IMAGE_NAME}:${IMAGE_TAG}
                            docker push ${IMAGE_NAME}:latest
                            docker logout
                        """
                    }
                }
            }
        }

        stage('Deploy to K8s') {
            steps {
                script {
                    withCredentials([file(
                        credentialsId: 'k3s-kubeconfig',
                        variable: 'KUBECONFIG'
                    )]) {
                        sh """
                            kubectl set image deployment/${DEPLOYMENT} \
                                ${CONTAINER}=${IMAGE_NAME}:${IMAGE_TAG} \
                                -n ${NAMESPACE} \
                                --kubeconfig=${KUBECONFIG}

                            kubectl rollout status deployment/${DEPLOYMENT} \
                                -n ${NAMESPACE} \
                                --kubeconfig=${KUBECONFIG} \
                                --timeout=120s
                        """
                    }
                }
            }
        }

    }

    post {
        success {
            echo "✅ Upload portal deployed successfully — ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "❌ Deployment failed — check logs above"
        }
        always {
            // Clean up local docker images to save disk space
            sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true"
        }
    }
}