podTemplate(
    //idleMinutes : 30,
    podRetention : onFailure(),
    activeDeadlineSeconds : 3600,
    containers: [
        containerTemplate(
            name: 'dtk-rpm-builder', 
            image: 'docker-production.packages.idmod.org/idm/dtk-rpm-builder:0.1',
            command: 'sleep', 
            args: '30d'
            )
  ]) {
  node(POD_LABEL) {
    container('dtk-rpm-builder'){
        stage('Cleanup Workspace') {
            cleanWs()
            echo "Cleaned Up Workspace For Project"
            echo "${params.BRANCH}"
        }
            stage('Prepare') {
                sh 'python3 --version'
                sh 'pip3 --version'
                sh 'python3 -m pip install --upgrade pip'
                sh "pip3 install wheel"
                sh "pip3 install build"
                sh 'python3 -m pip install --upgrade setuptools'
                sh 'pip3 freeze'
            }
        stage('Code Checkout') {
            if (env.CHANGE_ID) {
                echo "I execute on the pull request ${env.CHANGE_ID}"
                checkout([$class: 'GitSCM',
                    branches: [[name: "pr/${env.CHANGE_ID}/head"]],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [],
                    gitTool: 'Default',
                    submoduleCfg: [],
                    userRemoteConfigs: [[refspec: '+refs/pull/*:refs/remotes/origin/pr/*',
                                        credentialsId: '704061ca-54ca-4aec-b5ce-ddc7e9eab0f2',
                                        url: 'git@github.com:InstituteforDiseaseModeling/emod-api.git']]])
            } else {
             echo "Running on on ${env.BRANCH_NAME} branch"
                git branch: "${env.BRANCH_NAME}",
                credentialsId: '704061ca-54ca-4aec-b5ce-ddc7e9eab0f2',
                url: 'git@github.com:InstituteforDiseaseModeling/emod-api.git'   
            }
        }

        stage('Build') {
            sh 'pwd'
            sh 'ls -a'
            sh 'python3 -m build wheel'
        }
        stage('Install') {
            def curDate = sh(returnStdout: true, script: "date").trim()
             echo "The current date is ${curDate}"
             def wheelFile = sh(returnStdout: true, script: "find ./dist -name '*.whl'").toString().trim()
            echo "Package file: ${wheelFile}"
            sh "pip3 install $wheelFile --extra-index-url=https://packages.idmod.org/api/pypi/pypi-production/simple"
            sh 'pip3 install keyrings.alt'
            sh "pip3 freeze"
        }
        stage(' Unit Testing') {
            echo "Running Unit Tests"
            dir('tests') {
                sh "pip3 install unittest-xml-reporting"
                sh 'python3 -m xmlrunner discover'
                junit '*.xml'
            }
            dir('tests/unittests') {
                sh 'python3 -m xmlrunner discover'
                junit '*.xml'
            }
        }
    }
  }
}
