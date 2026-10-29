# Optional ToAPIs image script

The existing Gemini route is unchanged. This additive route reuses `generate.load_template` and needs only Python's standard library. Configure TOAPIS_API_KEY privately in the environment. The international origin is https://toapis.com, without /v1; the client appends /v1 once. No public script contains a Key.

```sh
python scripts/generate_toapis.py --prompt "An original ivory desk lamp on warm stone" --model gpt-image-2 --aspect 16:9 --size 1K --run-id reviewed-example
# Quotation only. Add --live only when you intend one paid create or a saved-task resume.
python scripts/generate_toapis.py --template path/to/template.md --vars '{"subject":"ivory desk lamp"}' --model gpt-image-2.5-flare --aspect 16:9 --size 1K --run-id reviewed-template
```

Supported: one image, gpt-image-2 or gpt-image-2.5-flare, 1K/2K/4K, 1:1/16:9/9:16. Other parameters, editing and video are not silently forwarded. Pricing is queried for the selected resolution, with a maximum quoted cost gate. The default is quotation-only. Keep `.toapis-state` and run ID unchanged for recovery. Polling is bounded and an uncertain POST never gets an automatic replacement POST.

On October 29, 2026 the optional CLI completed one gpt-image-2 / 1K generation, saved a decoded PNG and read $0.015 settled / 3 credits. This is a tested-Key receipt, not a universal tariff. Existing templates, default quote-only behavior, model/parameter restrictions and uncertain-submit handling pass offline tests. No GUI, edit or video acceptance is claimed.

`python -m unittest discover -s tests -p test_generate_toapis.py -v`

Provider/pricing requests and task responses stay local. Do not commit `.toapis-state`, output files, credentials or private receipt URLs. The billing helper distinguishes quoted/calculated cost from `billing.status=settled`.
