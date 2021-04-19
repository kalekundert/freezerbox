# Changelog

<!--next-version-placeholder-->

## v0.3.0 (2021-04-19)
### Feature
* Load synthesis and cleanups from excel ([`3d207d4`](https://github.com/kalekundert/freezerbox/commit/3d207d4b574bea2b3a66d954fd313a2093708b83))
* Reimplement `make` using a plugin-based architecture ([`948d868`](https://github.com/kalekundert/freezerbox/commit/948d868b5c4412f99d83230c3f90067fe6364c4d))
* Implement `group_by_synthesis/cleanup()` ([`746f14f`](https://github.com/kalekundert/freezerbox/commit/746f14fa27f4e3f39f01312172c04928b53a6323))
* Implement `grouped_topological_sort()` ([`93b399f`](https://github.com/kalekundert/freezerbox/commit/93b399f7ac893b4bc1751593ca6515d659c28431))
* Add intermediates and non-nucleic acid reagents ([`c2bb101`](https://github.com/kalekundert/freezerbox/commit/c2bb1011cac46f4e0530b5808ff697d893dbc681))
* Implement repr and str for Fields ([`0d705b8`](https://github.com/kalekundert/freezerbox/commit/0d705b8c4249240af9aeaaa7139df9b3aa5b5f25))
* Implement `Fields.__contains__()` ([`df1831b`](https://github.com/kalekundert/freezerbox/commit/df1831be9eb6f5fbfc44e26ddcc2962ed4f14655))
* Be more lazy about loading the database ([`37d79bf`](https://github.com/kalekundert/freezerbox/commit/37d79bf9c4eccd47a88dcc06659735865bcd16bf))
* Add tools for grouping protocols ([`7e2e5e0`](https://github.com/kalekundert/freezerbox/commit/7e2e5e02e35a6a531a353453cb1fe7ed938ce249))
* Add config classes for use with `appcli` ([`adcb836`](https://github.com/kalekundert/freezerbox/commit/adcb836337b51e332b046a0cf2300a7197ace8e3))
* Implement a more robust parser for synthesis/cleanup strings ([`cb76416`](https://github.com/kalekundert/freezerbox/commit/cb7641605b967d39a94c4db66ce0cb2aad5cd4b3))
* Allow sequences to expicitly identify as DNA or RNA ([`ab1f386`](https://github.com/kalekundert/freezerbox/commit/ab1f386a38d92eb2800c602e7bafdb3c22f2cda7))
* Allow temperatures to be floats ([`504afa1`](https://github.com/kalekundert/freezerbox/commit/504afa1416764fe40fd1586973bdd7b99931ebd3))
* Support the stock conc flag for the IVT protocol ([`be35387`](https://github.com/kalekundert/freezerbox/commit/be353877319e375604329ec49d1c34d87897f257))
* Allow oligo templates (e.g. ultramers) for PCR reactions ([`32d7c03`](https://github.com/kalekundert/freezerbox/commit/32d7c03cfb1e276b37f72b49465ad248ebd1fb21))
* Change default query attributes ([`f62c3c0`](https://github.com/kalekundert/freezerbox/commit/f62c3c04dd08ff4ee556b3be7a2d0058fe06c435))
* Add column for molecular weight ([`fbc1c79`](https://github.com/kalekundert/freezerbox/commit/fbc1c7909a7fc949c2e99aa2ba81c03f741858b8))

### Fix
* Distinguish merging from grouping when making combos ([`0a108cc`](https://github.com/kalekundert/freezerbox/commit/0a108cc352fe33abec819a28b7ea4189245ee8b8))
* Debug `Field.__getitem__()` ([`fe741b2`](https://github.com/kalekundert/freezerbox/commit/fe741b2f8443f92eab58543ddafbba102a6e052d))
* Ignore useless openpyxl warning ([`c082c54`](https://github.com/kalekundert/freezerbox/commit/c082c5429f056f0d4cd3b65fcad44c0dc2df0fea))
