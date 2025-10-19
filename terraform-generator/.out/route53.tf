data "aws_route53_zone" "root" {
  count        = False ? 1 : 0
  name         = "sentientops.com"
  private_zone = false
}

resource "aws_acm_certificate" "site"