# HTTP API
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"

  tags = var.tags
}

# Lambda integrations
resource "aws_apigatewayv2_integration" "no_adapter" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_no_adapter_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "with_adapter" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_with_adapter_invoke_arn
  payload_format_version = "2.0"
}

# Routes — need both {proxy+} and root routes since {proxy+} doesn't match /test1/ or /test2/ alone
resource "aws_apigatewayv2_route" "test1" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /test1/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.no_adapter.id}"
}

resource "aws_apigatewayv2_route" "test1_root" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /test1"
  target    = "integrations/${aws_apigatewayv2_integration.no_adapter.id}"
}

resource "aws_apigatewayv2_route" "test2" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /test2/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.with_adapter.id}"
}

resource "aws_apigatewayv2_route" "test2_root" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /test2"
  target    = "integrations/${aws_apigatewayv2_integration.with_adapter.id}"
}

# Auto-deploy stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true

  tags = var.tags
}

# Lambda permissions for API Gateway invocation
resource "aws_lambda_permission" "no_adapter" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_no_adapter_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "with_adapter" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_with_adapter_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
