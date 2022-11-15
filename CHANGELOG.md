# Changelog

<!--next-version-placeholder-->

## v0.26.0 (2022-09-05)
### Feature
* Improve maker plugin API ([`71fec2b`](https://github.com/kalekundert/freezerbox/commit/71fec2b3eca51d51a41cef1eded30b05098aa294))

### Fix
* Wrong option name in usage text ([`2bac1fd`](https://github.com/kalekundert/freezerbox/commit/2bac1fd072524aebb0c84de9223a165a580a0a53))
* Improve error messages when loading tags from Excel ([`10a435b`](https://github.com/kalekundert/freezerbox/commit/10a435b5701441cea56d408559f6c80dfbffc28a))

### Documentation
* Describe the role of the IntermediateMixin class ([`b42dc9f`](https://github.com/kalekundert/freezerbox/commit/b42dc9f1b77798e030da1c1c359eadf94ef56a66))

## v0.25.1 (2022-05-10)
### Fix
* Allow repr to fail gracefully ([`fa1e90c`](https://github.com/kalekundert/freezerbox/commit/fa1e90ceff8eac541e16379875df73199ca0adb0))

## v0.25.0 (2022-05-10)
### Feature
* Upgrade to BYOC ([`bf4dcd3`](https://github.com/kalekundert/freezerbox/commit/bf4dcd326a0d9cebbfa22dcb3d9bcdd896b64462))

## v0.24.0 (2022-04-19)
### Feature
* Support loading from specific XLSX worksheets ([`c98f0e0`](https://github.com/kalekundert/freezerbox/commit/c98f0e07fafe56819026af0840bc33646cfae805))

### Fix
* Fail gracefully if the database can't be loaded ([`2bd1037`](https://github.com/kalekundert/freezerbox/commit/2bd1037036e6fefaa19fb5a4a8ba6d1f41496003))
* Ignore leading/trailing whitespace in sequence strings ([`3a68766`](https://github.com/kalekundert/freezerbox/commit/3a6876616054b1ca50ca1d121806d49b6fc1b646))

## v0.23.0 (2022-01-04)
### Feature
* Read protein sequences from snapgene '.prot' files ([`4e0f1af`](https://github.com/kalekundert/freezerbox/commit/4e0f1af0e79a3c6265aa33f9f02dfa7f98cbdb3d))

## v0.22.0 (2021-11-30)
### Feature
* Allow small numbers of mismatches in feature sequences ([`ac5344c`](https://github.com/kalekundert/freezerbox/commit/ac5344c00c052a98f6572639c7632cb1b2b3780a))

## v0.21.0 (2021-11-30)
### Feature
* Add antibiotic fields ([`e3c71e6`](https://github.com/kalekundert/freezerbox/commit/e3c71e67dc614c3320ec1517b0367b310d0795ed))
* Allow ReagentConfig/ProductConfig to check reagent type ([`ff22066`](https://github.com/kalekundert/freezerbox/commit/ff220661f083feafdc654733b5b3751b1c5a32cd))

### Fix
* Maintain insertion order when merging dicts ([`abcf205`](https://github.com/kalekundert/freezerbox/commit/abcf205ec7a83829ef2798d8c2bbb72107d6ee51))
* Don't require dependencies to exist ([`cf07f92`](https://github.com/kalekundert/freezerbox/commit/cf07f9246bc0beda8627ac01ceb6a63cedacabb1))

## v0.20.2 (2021-10-28)
### Fix
* Don't shadow unintentional exceptions ([`baeee4c`](https://github.com/kalekundert/freezerbox/commit/baeee4c03a06f67f5eac7828677336bba74e5625))

## v0.20.1 (2021-10-23)
### Fix
* Don't require mw argument ([`c805155`](https://github.com/kalekundert/freezerbox/commit/c805155d932fa3c985fa1fa947205a6992999725))

## v0.20.0 (2021-10-21)
### Feature
* Refactor config, support plasmid features ([`9262f5e`](https://github.com/kalekundert/freezerbox/commit/9262f5e6c70fcb5d69f0d5a6107ccf3cd4855087))

## v0.19.0 (2021-10-21)
### Feature
* Refactor config, support plasmid features ([#22](https://github.com/kalekundert/freezerbox/issues/22)) ([`837f324`](https://github.com/kalekundert/freezerbox/commit/837f3248572b4178b443e461d20e7fc84a0a75b9))

## v0.18.2 (2021-08-26)
### Fix
* Control the sort order of all `make` targets ([`2dd79fb`](https://github.com/kalekundert/freezerbox/commit/2dd79fb9d1b172b48f08fa08c828c6bffe8a3e8d))

## v0.18.1 (2021-08-26)
### Fix
* Sort the list of targets passed to each maker ([`28ce569`](https://github.com/kalekundert/freezerbox/commit/28ce569ca04d6d414b981b15938e7a3123ea53b1))

## v0.18.0 (2021-08-25)
### Feature
* Add default and error arguments to unanimous() ([`b3c9612`](https://github.com/kalekundert/freezerbox/commit/b3c96123efd6bd32b9dbb2ccf9b02af23343b583))
* Add option to exclude tags from make protocol ([`aa6d056`](https://github.com/kalekundert/freezerbox/commit/aa6d0561b8622ebc9573d9c51d22c94ed46883d5))
* Allow µg/mL as a concentration unit ([`cc16e97`](https://github.com/kalekundert/freezerbox/commit/cc16e976f45010175886c97aa4e01358a6bb4ced))

### Fix
* Bug caused by new pandas version ([`e91f400`](https://github.com/kalekundert/freezerbox/commit/e91f400c1c786a23af990f4513a3780fcc1a5d3d))
* Prevent the stepwise maker from shadowing attributes ([`fa2460e`](https://github.com/kalekundert/freezerbox/commit/fa2460eb3cf5a1f796a13a226ce92c93c0aae551))
* Improve the repr for deferred values ([`86eda4b`](https://github.com/kalekundert/freezerbox/commit/86eda4b5521455168ef4f6e01083944dbab877ac))
* Correctly handle quoted stepwise commands ([`5b0dfd1`](https://github.com/kalekundert/freezerbox/commit/5b0dfd1b31fa0181ef22665c11c99f0d7dd0805c))
* Correctly parse unicode quotes ([`583e191`](https://github.com/kalekundert/freezerbox/commit/583e191a219281437352c10c697a69f28e4ed625))
* Ignore openpyxl/numpy warning ([`9a2ab5b`](https://github.com/kalekundert/freezerbox/commit/9a2ab5b88871d0ffbb4f4212f63eb084370dcd94))
* Correctly initialize dilute from products ([`4d9d2ca`](https://github.com/kalekundert/freezerbox/commit/4d9d2ca1f06d9ef443e806da55e12918e421ce97))

## v0.17.0 (2021-06-28)
### Feature
* Give database a default name ([`6ebbecd`](https://github.com/kalekundert/freezerbox/commit/6ebbecd09ba661baa019a4a0b48f0f15f6caada0))
* Add setup arguments to ProductConfig ([`1d5bb5e`](https://github.com/kalekundert/freezerbox/commit/1d5bb5e12672c2ed951f1eed3aa0c63e6c486129))
* Add setup arguments to ReagentConfig ([`1f88626`](https://github.com/kalekundert/freezerbox/commit/1f8862629c43c886d5b0aa2ba51982b5e7a4bebe))
* Assign the stepwise plugin a priority ([`d28a0dc`](https://github.com/kalekundert/freezerbox/commit/d28a0dc2444b5090243ebe4a06651d345690029e))

## v0.16.0 (2021-06-21)
### Feature
* Migrate to new Config architecture (logging) ([`acbc1e6`](https://github.com/kalekundert/freezerbox/commit/acbc1e62868bf9d2c70823bbaf92604b60b2d37d))
* Rename the 'pending' column to 'ready' ([`dd309ac`](https://github.com/kalekundert/freezerbox/commit/dd309ac815a1add0923cf9b1173c981dda952cc4))

## v0.15.0 (2021-06-14)
### Feature
* Teach make how to find dependencies ([`92cac73`](https://github.com/kalekundert/freezerbox/commit/92cac7336d3c571cdaa11a81469031940242e7cb))
* Show the step number for intermediate reagents ([`e3f2546`](https://github.com/kalekundert/freezerbox/commit/e3f2546fa4da5382aa61aaf1de245b62876fd89a))
* Add a volume field to molecules ([`2f8b702`](https://github.com/kalekundert/freezerbox/commit/2f8b7027f8df6abc674efbd902de1239f85cde31))

## v0.14.1 (2021-06-07)
### Fix
* Allow non-string keys ([`e41378e`](https://github.com/kalekundert/freezerbox/commit/e41378e2fe17e59266d685401e59eadb127f33a5))

## v0.14.0 (2021-06-04)
### Feature
* Add the *keys* argument to `iter_combos()` ([`d93d239`](https://github.com/kalekundert/freezerbox/commit/d93d239dfd07099a472e92efa63c29ada3ff5fe3))

## v0.13.0 (2021-06-03)
### Feature
* Parse quantities with or without units ([`c6251d5`](https://github.com/kalekundert/freezerbox/commit/c6251d531e61220eb952bc5e75c2160cc52c0bcc))

## v0.12.0 (2021-06-02)
### Feature
* Infer molecular weight from length ([`94a2d80`](https://github.com/kalekundert/freezerbox/commit/94a2d801523a8f4833a77266dfd09bbb5abec3d2))

## v0.11.0 (2021-06-01)
### Feature
* Allow conversions to/from µg/µL ([`c8e46b1`](https://github.com/kalekundert/freezerbox/commit/c8e46b1789e9712a469d6cd172177e47824fe5d9))

## v0.10.1 (2021-05-05)
### Fix
* Respect empty databases ([`c81a511`](https://github.com/kalekundert/freezerbox/commit/c81a5112b05452a7be9d360f6ff152b45b478810))

## v0.10.0 (2021-05-05)
### Feature
* Add dependency getter to `Reagent` class ([`fb40b17`](https://github.com/kalekundert/freezerbox/commit/fb40b170a6d5668e172b662cd60135ecc9c59bb5))
* Add `parse_mass_ug()` ([`37a4e4c`](https://github.com/kalekundert/freezerbox/commit/37a4e4c229cec697f98200caef1ed3350d53477c))

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
