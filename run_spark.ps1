param(
    [string]$KafkaBootstrap = "localhost:9092",
    [string]$Topic = "raw_posts",
    [string]$PredictionsTopic = "predictions",
    [string]$JavaHome = "C:\Program Files\Java\jdk-17.0.12"
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sparkHome = (Resolve-Path "$projectRoot\.venv\Lib\site-packages\pyspark").Path
$pythonExe = (Resolve-Path "$projectRoot\.venv\Scripts\python.exe").Path
$scriptPath = Join-Path $projectRoot "analytics\spark_consumer.py"

if (-not (Test-Path "$JavaHome\bin\java.exe")) {
    Write-Error "Java 17 not found at '$JavaHome'. Pass -JavaHome with a valid JDK 17 path."
    exit 1
}

$env:JAVA_HOME = $JavaHome
$env:Path = "$JavaHome\bin;$env:Path"
$env:SPARK_HOME = $sparkHome
$env:PYSPARK_PYTHON = $pythonExe
$env:PYSPARK_DRIVER_PYTHON = $pythonExe

& "$sparkHome\bin\spark-submit.cmd" `
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5 `
  $scriptPath `
  --kafka-bootstrap $KafkaBootstrap `
  --topic $Topic `
  --predictions-topic $PredictionsTopic
