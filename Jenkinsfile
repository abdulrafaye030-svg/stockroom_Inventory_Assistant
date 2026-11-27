pipeline {
  agent any
  triggers { pollSCM('H/2 * * * *') }
  stages {
    stage('Build') {
      steps {
        bat 'npm ci'
        bat 'npm run build'
        powershell 'Compress-Archive -Path dist\\* -DestinationPath stockroom.zip -Force'
      }
    }
    stage('Test') {
      steps {
        bat 'npm test -- --run'
        bat 'py -m unittest discover tests'
      }
    }
    stage('Deploy') {
      steps {
        powershell 'New-Item -ItemType Directory -Force C:\\stockroom-deployed | Out-Null; Copy-Item dist, server.py, chatbot.py, database.py -Destination C:\\stockroom-deployed -Recurse -Force'
      }
    }
  }
  post {
    success { archiveArtifacts artifacts: 'stockroom.zip' }
  }
}