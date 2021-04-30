# Changelog

<!--next-version-placeholder-->

## v0.9.0 (2021-04-30)
### Feature
* Add the `dilute` protocol ([`ffe0276`](https://github.com/kalekundert/freezerbox/commit/ffe02769dfddb84802634cbc9c99627ccad0a765))

### Documentation
* Describe how to specify protocols for use with make ([`6df0a9b`](https://github.com/kalekundert/freezerbox/commit/6df0a9b91490be53f48262007f68b09c12952cf9))

## v0.8.0 (2021-04-27)
### Feature
* Expand ~ in directory fields ([`4e0e8b7`](https://github.com/kalekundert/freezerbox/commit/4e0e8b789bc296e85d7a04fbae09f5ed0fa98036))
* Integrate the stepwise maker with exmemo ([`4a69ad9`](https://github.com/kalekundert/freezerbox/commit/4a69ad9261cafbe0508564e160a73206300fa652))

## v0.7.0 (2021-04-27)
### Feature
* Merge stepwise makers with identical protocols ([`8225267`](https://github.com/kalekundert/freezerbox/commit/822526735fed5cfa084b291ddfa7189fe5795f3d))
* Add functions for joining lists/dicts/sets ([`bc44d7a`](https://github.com/kalekundert/freezerbox/commit/bc44d7a43a69258453024c7a0a8cab199b948edb))

## v0.6.0 (2021-04-26)
### Feature
* Add built-in `sw` and `order` makers ([`165630a`](https://github.com/kalekundert/freezerbox/commit/165630aedc992953e21ea90c9a4a28076c4a3e9e))

## v0.5.0 (2021-04-26)
### Feature
* Add functions to parse minutes and hours ([`db69545`](https://github.com/kalekundert/freezerbox/commit/db695453e6198fe6ad2aeaa69727407edc45916c))

### Fix
* Debug error message ([`3cf8850`](https://github.com/kalekundert/freezerbox/commit/3cf88501bfa80945dfb16d2ca00a12d9be75024a))
* Support grouping non-sortable values ([`cf0bb2b`](https://github.com/kalekundert/freezerbox/commit/cf0bb2b4ee79a871c4264427d2d77a0f0cc40e09))

## v0.4.2 (2021-04-23)
### Fix
* Update dependencies ([`1124099`](https://github.com/kalekundert/freezerbox/commit/11240990585a7a76bb4b4703f5681d96b59fde5f))

## v0.4.1 (2021-04-23)
### Fix
* Raise QueryError if molecular weight calculation fails. ([`aac3195`](https://github.com/kalekundert/freezerbox/commit/aac3195a5b50660c2be73b968dd9ce1429631fdf))

## v0.4.0 (2021-04-23)
### Feature
* Pass database to maker factories ([`52bb4d3`](https://github.com/kalekundert/freezerbox/commit/52bb4d3afd7ac94f85b2edde226002ff7fe0d1bb))
* Give `iter_combo_makers()` a factory argument ([`31cbc0e`](https://github.com/kalekundert/freezerbox/commit/31cbc0e69c00dbb0f5805ec7c62fb0902e4f3c55))
* Add `unanimous()` ([`d611a49`](https://github.com/kalekundert/freezerbox/commit/d611a492526bf4d4d9110baf3096e32561e063cb))

### Fix
* Correctly merge products ([`0f9e5b6`](https://github.com/kalekundert/freezerbox/commit/0f9e5b6b25339e2eec5a9d864b7656b0c9ef3f84))
* Main modules cannot use relative imports ([`c5e444e`](https://github.com/kalekundert/freezerbox/commit/c5e444ee5061bbc08a2c16891e862a3bf45331e2))
* Load maker entry points ([`606b72d`](https://github.com/kalekundert/freezerbox/commit/606b72de014bd66bc5e9a66431e33a61d7aef1fa))
* Allow any non-control character in unquoted words ([`d53426c`](https://github.com/kalekundert/freezerbox/commit/d53426c52fd47b99dc4f7492270ef5284ef50357))

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
