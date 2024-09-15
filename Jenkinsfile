podTemplate(cloud: 'OpenShift', label: 'rpmbuild') {
  node('rpm-based') {
    container('dtk-build'){
		stage('Cleanup Workspace') {
			cleanWs()
			echo "Cleaned Up Workspace For Project"
			echo "${params.BRANCH}"
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
                userRemoteConfigs: [[refspec: '+refs/pull/*:refs/remotes/origin/pr/*', credentialsId: '704061ca-54ca-4aec-b5ce-ddc7e9eab0f2', url: 'git@github.com:InstituteforDiseaseModeling/emod-api.git']]])
            } else {
				echo "I execute on the ${env.BRANCH_NAME} branch"
                git branch: "${env.BRANCH_NAME}",
    			credentialsId: '704061ca-54ca-4aec-b5ce-ddc7e9eab0f2',
    			url: 'git@github.com:InstituteforDiseaseModeling/emod-api.git'   
            }
        }
		stage('Prepare') {
			sh 'python --version'
			sh 'python3.6 --version'
			sh 'pip3.6 --version'

			sh 'python3.6 -m pip install --upgrade pip'
			//sh 'python3.6 -m pip install --upgrade wheel'
			sh "pip3.6 install wheel"
			sh 'python3.6 -m pip install --upgrade setuptools'
			sh 'pip3.6 freeze'
		}
		stage('Build') {
			sh 'pwd'
			sh 'ls -a'
			//sh 'python3.6 -m build'
			sh 'python3.6 package_setup.py bdist_wheel'
		}
		stage('Install') {
			def curDate = sh(returnStdout: true, script: "date").trim()
            echo "The current date is ${curDate}"
            def wheelFile = sh(returnStdout: true, script: "find ./dist -name '*.whl'").toString().trim()
			//def wheelFile = sh(returnStdout: true, script: "python3.6 ./.github/scripts/get_wheel_filename.py --package-file package_setup.py").toString().trim()
			echo "This is the package file: ${wheelFile}"
			sh "pip3.6 install $wheelFile"
			sh "pip3.6 freeze"
		}
        stage(' Unit Testing') {
            echo "Running Unit Tests"
            dir('tests') {
                sh "pip3.6 install unittest-xml-reporting"
                sh 'python3.6 -m xmlrunner discover'
                junit '*.xml'
            }
            dir('tests/unittests') {
                    sh 'python3.6 -m xmlrunner discover'
                    junit '*.xml'
            }
        }
    }
  }
}
