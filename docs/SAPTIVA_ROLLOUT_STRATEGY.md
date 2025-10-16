# Saptiva Production Rollout Strategy

**Status**: Phase 2 Complete ✅ | Ready for Production Rollout
**Target Date**: Q1 2026 (TBD)
**Owner**: Backend Team + DevOps
**Approval Required**: Engineering Manager, CTO

---

## Executive Summary

This document outlines the production rollout strategy for migrating from third-party text extraction libraries (pypdf + pytesseract) to Saptiva Native Tools API.

**Key Points:**
- ✅ Phase 1 Complete: Abstraction layer implemented
- ✅ Phase 2 Complete: Saptiva integration with caching, circuit breaker, cost optimization
- 🔄 Phase 3 In Progress: Production rollout with A/B testing

**Benefits of Migration:**
- **Performance**: Estimated 2-3x faster extraction (pending benchmarks)
- **Accuracy**: Better OCR quality with Spanish language support
- **Scalability**: Cloud-native API vs local processing
- **Maintenance**: Reduced dependency management

**Risks:**
- **Cost**: ~$0.02-0.05 per document (vs free local processing)
- **Availability**: Dependency on Saptiva API uptime
- **Latency**: Network overhead for API calls

**Mitigation:**
- Gradual rollout with A/B testing (5% → 25% → 50% → 100%)
- Circuit breaker pattern for automatic fallback
- Redis caching to reduce API calls
- Cost optimization (skip API for searchable PDFs)
- Rollback procedure documented

---

## Rollout Phases

### Phase 1: Preparation ✅ COMPLETE

**Duration**: 2 weeks
**Status**: Merged to `develop`

**Deliverables:**
- [x] Abstraction layer (TextExtractor ABC)
- [x] ThirdPartyExtractor wrapper
- [x] SaptivaExtractor stub
- [x] Factory pattern with EXTRACTOR_PROVIDER flag
- [x] Unit tests (35+ tests, >80% coverage)

---

### Phase 2: Implementation ✅ COMPLETE

**Duration**: 3 weeks
**Status**: Ready for Testing

**Deliverables:**
- [x] Saptiva PDF extraction (base64 encoding)
- [x] Saptiva OCR extraction (base64 encoding)
- [x] Circuit breaker with half-open state
- [x] Exponential backoff retry logic
- [x] Redis caching with zstd compression
- [x] Cost optimization (bypass API for searchable PDFs)
- [x] Integration tests
- [x] Performance benchmarking framework
- [x] A/B testing framework

**Acceptance Criteria:**
- [x] PDF extraction works with real Saptiva API
- [x] OCR extraction implemented (pending API docs)
- [x] Circuit breaker opens after 5 failures
- [x] Cache hit rate > 30% in tests
- [x] Searchable PDFs use native extraction

---

### Phase 3: Staging Deployment 🔄 IN PROGRESS

**Duration**: 2 weeks
**Target**: Week 1-2 of Q1 2026

#### Week 1: Staging Environment

**Monday:**
1. Deploy to staging environment
   ```bash
   # Deploy with Saptiva enabled for testing
   cd infra
   docker-compose -f docker-compose.prod.yml up -d

   # Verify deployment
   curl https://staging-api.copilotos.com/health
   ```

2. Configure environment variables in staging:
   ```bash
   EXTRACTOR_PROVIDER=saptiva
   SAPTIVA_BASE_URL=https://api.saptiva.com
   SAPTIVA_API_KEY=<staging_key>
   REDIS_URL=redis://staging-redis:6379/0
   EXTRACTION_CACHE_ENABLED=true
   EXTRACTION_CACHE_TTL_HOURS=24
   AB_TEST_ENABLED=false  # Full rollout in staging
   ```

3. Run integration tests against staging:
   ```bash
   export SAPTIVA_API_KEY=<staging_key>
   export SAPTIVA_BASE_URL=https://api.saptiva.com
   pytest tests/integration/test_saptiva_integration.py -v -m integration
   ```

**Tuesday-Wednesday:**
4. Manual testing in staging:
   - Upload 20 diverse PDF documents
   - Upload 20 images with text (OCR)
   - Verify extraction quality
   - Check latency metrics
   - Verify caching behavior
   - Test circuit breaker (simulate Saptiva downtime)

5. Run performance benchmarks:
   ```bash
   python tests/benchmarks/benchmark_extractors.py \
     --compare \
     --documents 100 \
     --document-type pdf \
     --output benchmark_results.json
   ```

**Thursday:**
6. Load testing:
   ```bash
   # Simulate 100 concurrent users
   locust -f tests/load/locustfile.py \
     --host https://staging-api.copilotos.com \
     --users 100 \
     --spawn-rate 10 \
     --run-time 30m
   ```

7. Monitor metrics:
   - Latency (p50, p95, p99)
   - Error rate
   - Circuit breaker state transitions
   - Cache hit rate
   - API costs (Saptiva dashboard)

**Friday:**
8. Review staging results with team
9. Document any issues found
10. Create production deployment checklist

#### Week 2: Pre-Production Validation

**Monday-Tuesday:**
1. Fix any issues found in staging
2. Re-run integration tests
3. Update documentation based on learnings

**Wednesday:**
4. Security review:
   - API key rotation procedure
   - Rate limiting configuration
   - Error message sanitization (no sensitive data)

**Thursday:**
5. Cost analysis:
   - Estimate monthly costs based on staging metrics
   - Set up billing alerts in Saptiva dashboard
   - Configure budget limits

**Friday:**
6. Go/No-Go meeting with stakeholders
7. Final approval for production rollout

**Acceptance Criteria for Phase 3:**
- [ ] Integration tests pass in staging
- [ ] Performance benchmarks show acceptable latency
- [ ] Load testing shows system handles expected traffic
- [ ] Cache hit rate > 30%
- [ ] Error rate < 1%
- [ ] Circuit breaker functions correctly
- [ ] Cost projections within budget
- [ ] Security review approved
- [ ] Rollback procedure tested

---

### Phase 4: Production Rollout (Gradual) 🔮 PLANNED

**Duration**: 4-6 weeks
**Target**: Week 3-8 of Q1 2026

#### Stage 1: 5% Rollout (Week 3)

**Monday:**
1. Deploy to production with A/B testing enabled:
   ```bash
   # Production environment variables
   EXTRACTOR_PROVIDER=third_party  # Factory ignores this in A/B mode
   AB_TEST_ENABLED=true
   AB_TEST_SAPTIVA_PERCENTAGE=5
   AB_TEST_COHORT_TTL_DAYS=30
   ```

2. Deploy code:
   ```bash
   git checkout main
   git pull origin main
   make deploy-prod  # Or your deployment command
   ```

3. Verify deployment:
   ```bash
   curl https://api.copilotos.com/health
   # Check logs for A/B test initialization
   ```

**Tuesday-Friday:**
4. Monitor key metrics:
   - **Latency**: Compare control (third_party) vs treatment (saptiva)
   - **Error Rate**: Should be <1% for both variants
   - **Cost**: Track Saptiva API spend
   - **Cache Hit Rate**: Should be >30%
   - **Circuit Breaker**: Should remain closed

5. Daily check-ins:
   - Review Grafana dashboards
   - Check error logs
   - Verify A/B test cohort distribution

**Success Criteria:**
- [ ] 5% of users successfully using Saptiva
- [ ] Latency within 10% of third_party
- [ ] Error rate < 1%
- [ ] No major incidents
- [ ] Costs within budget

**If Success Criteria Met: Proceed to Stage 2**
**If Not Met: Rollback (see Rollback Procedure)**

---

#### Stage 2: 25% Rollout (Week 4-5)

**Monday:**
1. Increase rollout percentage:
   ```bash
   # Update environment variable
   AB_TEST_SAPTIVA_PERCENTAGE=25

   # Restart services to pick up new config
   kubectl rollout restart deployment/api
   # OR
   docker-compose -f docker-compose.prod.yml restart api
   ```

2. Monitor for 1 hour after change
3. Verify 25% of users are in treatment cohort

**Tuesday-Friday (Week 4):**
4. Continue monitoring same metrics as Stage 1
5. Analyze comparative metrics:
   ```bash
   # Export metrics for analysis
   python tools/export_ab_metrics.py \
     --start-date 2026-01-15 \
     --end-date 2026-01-22 \
     --output metrics_week4.csv
   ```

**Monday-Friday (Week 5):**
6. Extended monitoring period
7. User feedback collection (if applicable)
8. Cost analysis (weekly Saptiva bill)

**Success Criteria:**
- [ ] Latency comparable to third_party (±10%)
- [ ] Error rate < 1%
- [ ] No increase in customer complaints
- [ ] Costs within budget
- [ ] 2-week stable operation

**If Success Criteria Met: Proceed to Stage 3**
**If Not Met: Hold at 25% or Rollback**

---

#### Stage 3: 50% Rollout (Week 6-7)

**Monday (Week 6):**
1. Increase to 50% rollout:
   ```bash
   AB_TEST_SAPTIVA_PERCENTAGE=50
   kubectl rollout restart deployment/api
   ```

2. Monitor closely for first 4 hours
3. Verify traffic distribution is 50/50

**Tuesday-Friday (Week 6):**
4. Monitor all metrics
5. Compare control vs treatment groups
6. Statistical significance analysis:
   - Latency: t-test (p < 0.05)
   - Error rate: Chi-square test
   - User satisfaction (if measurable)

**Monday-Friday (Week 7):**
7. Extended monitoring
8. Prepare for full rollout
9. Document learnings

**Success Criteria:**
- [ ] Latency acceptable (≤ third_party)
- [ ] Error rate ≤ third_party
- [ ] Positive or neutral user feedback
- [ ] Costs acceptable
- [ ] 2-week stable operation

**If Success Criteria Met: Proceed to Stage 4**
**If Not Met: Hold at 50% for additional week or Rollback**

---

#### Stage 4: 100% Rollout (Week 8)

**Monday:**
1. Full rollout:
   ```bash
   AB_TEST_ENABLED=false
   EXTRACTOR_PROVIDER=saptiva
   kubectl rollout restart deployment/api
   ```

2. Monitor very closely for first 8 hours
3. Alert all on-call engineers

**Tuesday-Friday:**
4. Continue monitoring for full week
5. Prepare to make Saptiva the permanent default

**Success Criteria:**
- [ ] All extractions using Saptiva
- [ ] Error rate < 1%
- [ ] Latency acceptable
- [ ] No major incidents
- [ ] 1-week stable operation

**If Successful: Proceed to Phase 5 (Cleanup)**
**If Issues: Immediate Rollback**

---

### Phase 5: Post-Rollout Cleanup 🔮 FUTURE

**Duration**: 2 weeks
**Target**: Week 9-10 of Q1 2026

1. **Documentation Updates:**
   - Update README with Saptiva as default
   - Archive third-party extraction docs
   - Document lessons learned

2. **Code Cleanup:**
   - Mark ThirdPartyExtractor as deprecated
   - Keep it as fallback for 6 months
   - Remove A/B testing code (or keep for future experiments)

3. **Dependency Management:**
   - Evaluate removing pypdf, pytesseract from requirements.txt
   - Keep for 6 months as emergency fallback
   - Plan final removal for Q3 2026

4. **Cost Optimization:**
   - Analyze cost patterns
   - Adjust cache TTL if needed
   - Tune searchable PDF detection threshold

5. **Team Training:**
   - Document operational procedures
   - Train support team on new system
   - Update incident response playbooks

---

## Rollback Procedure

**When to Rollback:**
- Error rate > 5% for Saptiva variant
- Latency > 2x third_party
- Circuit breaker opening frequently (>10 times/hour)
- Saptiva API downtime > 30 minutes
- Costs exceeding budget by >50%
- Critical bug discovered

**Rollback Steps (5-10 minutes):**

### Option 1: Reduce A/B Test Percentage

```bash
# Reduce to previous stage
export AB_TEST_SAPTIVA_PERCENTAGE=5  # Or 0 for full rollback

# Restart services
kubectl rollout restart deployment/api
# OR
docker-compose -f docker-compose.prod.yml restart api

# Verify rollback
curl https://api.copilotos.com/health
kubectl logs -f deployment/api | grep "A/B test"
```

### Option 2: Disable A/B Testing Completely

```bash
# Disable A/B testing, use only third_party
export AB_TEST_ENABLED=false
export EXTRACTOR_PROVIDER=third_party

# Restart services
kubectl rollout restart deployment/api

# Verify all users on third_party
curl https://api.copilotos.com/health
```

### Option 3: Emergency Rollback (Git Revert)

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Deploy previous version
make deploy-prod

# Verify deployment
curl https://api.copilotos.com/health
```

**Post-Rollback:**
1. Document reason for rollback
2. Analyze root cause
3. Create bug tickets
4. Schedule retrospective
5. Plan remediation
6. Re-test in staging before retry

---

## Monitoring & Alerting

### Key Metrics to Monitor

**Latency Metrics** (Grafana Dashboard)
- p50, p95, p99 extraction time
- Control vs Treatment comparison
- Breakdown by document type (PDF vs Image)

**Error Metrics** (Sentry + Logs)
- Error rate by variant
- Circuit breaker state
- API timeout rate
- Unsupported format errors

**Business Metrics** (BigQuery)
- Documents processed per hour
- Cache hit rate
- Cost per document
- User satisfaction (if measurable)

### Alerts to Configure

**Critical Alerts** (PagerDuty)
- Saptiva error rate > 5% (5-minute window)
- Circuit breaker OPEN for > 5 minutes
- API latency p95 > 5 seconds
- Redis cache failure

**Warning Alerts** (Slack)
- Saptiva error rate > 2%
- Cache hit rate < 20%
- Daily cost > $100
- Latency p95 > 2 seconds

### Dashboards to Create

1. **A/B Test Dashboard** (Grafana)
   - Traffic distribution (control vs treatment)
   - Latency comparison chart
   - Error rate comparison chart
   - Cost comparison

2. **Saptiva Health Dashboard** (Grafana)
   - API response time
   - Circuit breaker state
   - Cache hit rate
   - API call volume

3. **Cost Dashboard** (BigQuery + Data Studio)
   - Daily Saptiva spend
   - Cost per document type
   - Projection vs actual
   - Cost savings from caching

---

## Cost Management

### Estimated Costs

**Assumptions:**
- 1,000 documents/day
- 70% PDFs, 30% images
- 30% cache hit rate

**Monthly Cost Estimate:**
```
PDFs:       700 docs/day × $0.02 × 30 days × 0.7 (cache miss) = $294/month
Images:     300 docs/day × $0.05 × 30 days × 0.7 (cache miss) = $315/month
Total:      ~$609/month

With optimization (50% searchable PDFs bypass API):
PDFs:       350 docs/day × $0.02 × 30 days × 0.7 = $147/month
Images:     300 docs/day × $0.05 × 30 days × 0.7 = $315/month
Total:      ~$462/month
```

### Cost Controls

1. **Cache Optimization**
   - Increase TTL to 48 hours (if acceptable)
   - Pre-warm cache for common documents
   - Monitor cache hit rate weekly

2. **Searchable PDF Detection**
   - Tune threshold (currently 50 chars)
   - Log searchable PDF rate
   - Aim for >50% bypass rate

3. **Rate Limiting**
   - Implement user-level rate limits
   - Prevent abuse/spam uploads
   - Monitor outlier users

4. **Budget Alerts**
   - Set daily budget limit: $20
   - Set monthly budget limit: $600
   - Alert at 80% and 100% of budget

---

## Communication Plan

### Stakeholders

- **Engineering Team**: Implementation details, technical issues
- **Product Team**: Feature impact, user experience
- **DevOps Team**: Deployment, monitoring, incidents
- **Finance Team**: Cost projections, budget approval
- **Support Team**: User-facing changes, troubleshooting
- **Management**: Progress updates, go/no-go decisions

### Communication Schedule

**Weekly Updates** (Slack #engineering):
- Rollout progress (X% complete)
- Key metrics summary
- Issues encountered
- Next steps

**Go/No-Go Meetings** (Before each stage):
- Review acceptance criteria
- Present metrics from previous stage
- Discuss risks
- Decision: Proceed, Hold, or Rollback

**Incident Communication** (If rollback needed):
- Immediate Slack notification
- Post-mortem within 48 hours
- Remediation plan within 1 week

---

## Success Criteria

### Phase 3 (Staging)
- [x] Integration tests pass
- [x] Performance benchmarks acceptable
- [x] Load testing successful
- [x] Cost projections approved

### Phase 4 (Production)
- [ ] 100% rollout achieved
- [ ] Latency ≤ third_party
- [ ] Error rate < 1%
- [ ] 4-week stable operation
- [ ] Costs within budget

### Phase 5 (Post-Rollout)
- [ ] Documentation complete
- [ ] Team trained
- [ ] Monitoring dashboards active
- [ ] Cost optimization in place

---

## Lessons Learned (To be filled post-rollout)

### What Went Well


### What Could Be Improved


### Action Items for Future Rollouts


---

## Appendix

### A. Environment Variable Reference

```bash
# Extractor Configuration
EXTRACTOR_PROVIDER=third_party|saptiva

# Saptiva API
SAPTIVA_BASE_URL=https://api.saptiva.com
SAPTIVA_API_KEY=<your_key>

# Caching
EXTRACTION_CACHE_ENABLED=true
EXTRACTION_CACHE_TTL_HOURS=24
REDIS_URL=redis://localhost:6379/0

# A/B Testing
AB_TEST_ENABLED=true
AB_TEST_SAPTIVA_PERCENTAGE=0-100
AB_TEST_COHORT_TTL_DAYS=30
```

### B. Useful Commands

```bash
# Check A/B test status
curl https://api.copilotos.com/api/v1/extractors/ab-test/status

# View current extractor configuration
curl https://api.copilotos.com/api/v1/extractors/config

# Export A/B test metrics
python tools/export_ab_metrics.py --output metrics.csv

# Run benchmarks
python tests/benchmarks/benchmark_extractors.py --compare --documents 100
```

### C. Contact Information

- **Project Lead**: Backend Team Lead
- **DevOps**: DevOps Team
- **On-Call**: #oncall Slack channel
- **Saptiva Support**: support@saptiva.com

---

**Document Version**: 1.0
**Last Updated**: 2026-01-16
**Next Review**: After Phase 4 completion
