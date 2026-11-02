# Revisión particular — prisma 30-1994

**Hechos observados:** 35 registros, 15 evaluables y 20 no evaluables. Aparece únicamente en entrenamiento, desde 2013-11-20 15:49:21 hasta 2013-12-17 18:35:24. Cada método marca sus 15 observaciones evaluables con q99. Se conserva íntegro, sin reajustar modelos.

Sus scores y estados son retrospectivos y condicionados al modelo ajustado al final de entrenamiento. No estaban disponibles como resultados operativos en esas fechas; todas sus filas tienen `model_available_at_observation=False`.

Se genera 1 episodio con ventana de 72 h. La cadena de marcas dura 237.741389 horas: puede superar 72 horas porque esta ventana limita la separación **entre marcas consecutivas**, no la duración máxima del episodio. Las 15 marcas coinciden entre métodos; las políticas unión, consenso e híbrida seleccionan 15 filas y persistencia selecciona 14. Los 20 registros no evaluables preceden al episodio y mantienen sus motivos; no cuentan como interrupciones internas de ese episodio.

| episode_id | prism_id | start_timestamp | last_observed_timestamp | last_mark_timestamp | duration_hours | mark_span_hours | closure_status | closure_observed_at | expiry_timestamp | record_count | eligible_record_count | ineligible_record_count | baseline_mark_count | iforest_mark_count | union_mark_count | agreement_count | maximum_baseline_score | maximum_iforest_score | periods_observed | candidate_policies | quality_interruption_flag | predominant_baseline_component |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_378ba9e255f13442c33d4029 | 30-1994 | 2013-12-07 20:50:55 | 2013-12-17 18:35:24 | 2013-12-17 18:35:24 | 237.741389 | 237.741389 | censurado_fin_del_prisma | — | 2013-12-20 18:35:24 | 15 | 15 | 0 | 15 | 15 | 15 | 15 | 80.463332 | 0.857048 | entrenamiento | union;consensus;persistence;hybrid | False | trend |

## Comparación descriptiva con entrenamiento

| scope | model | eligible_rows | min_score | median_score | maximum_score | q99_frozen |
| --- | --- | --- | --- | --- | --- | --- |
| entrenamiento_evaluable | baseline | 2909 | 0.007831 | 0.720073 | 80.463332 | 4.439772 |
| entrenamiento_evaluable | isolation_forest | 2909 | 0.342612 | 0.387 | 0.857048 | 0.587293 |
| 30-1994_evaluable | baseline | 15 | 7.605273 | 46.33377 | 80.463332 | 4.439772 |
| 30-1994_evaluable | isolation_forest | 15 | 0.748886 | 0.840964 | 0.857048 | 0.587293 |

Los componentes de la regla se calculan con referencias y pesos ya congelados. El componente predominante, sumado sobre marcas del episodio, es `trend`. Las mayores desviaciones guardadas por registro son evidencia descriptiva; **no son una atribución causal del Isolation Forest**. Las columnas de componentes permiten comprobar exactamente el score de la regla con los valores originales de Fase 4.

## Evidencia completa por observación

Los identificadores enlazan con los originales. Vacíos numéricos y marcas desconocidas se muestran como “—”; no se convierten en cero ni en ausencia de marca.

| source_record_id | timestamp | model_eligible | model_ineligibility_reason | baseline_score | isolation_forest_score | baseline_training_percentile | isolation_forest_training_percentile | baseline_mark_q99 | iforest_mark_q99 | episode_id | causal_state | baseline_component_historical_z | baseline_component_trend | baseline_component_persistence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a963ce00e970cad746a9f481f2feadba9db18799b30f71f70c951d5b7b05d986 | 2013-11-20 15:49:21 | False | sin historia previa; historia previa insuficiente; cobertura 72h insuficiente; cobertura 7d insuficiente; característica indispensable faltante; demasiadas características faltantes | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 8f029f02eca2891d042cf0c7c945ebc8deb6f1d543b733db77071458dcb40fc2 | 2013-11-28 12:16:00 | False | historia previa insuficiente; hueco prolongado; cobertura 72h insuficiente; cobertura 7d insuficiente; característica indispensable faltante; demasiadas características faltantes | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| cb7b302a99963b19fc01764ef3b80a17231c214e3c639497b46204b15f0947a8 | 2013-11-28 22:32:23 | False | historia previa insuficiente; cobertura 72h insuficiente; cobertura 7d insuficiente; característica indispensable faltante; demasiadas características faltantes | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 8b9fca8ac69cb0a23b5b1b0be95497b5a30f2ab5eb3c8985bdd183361ef937ba | 2013-11-30 11:11:26 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 47efc036b07d5ea29e7b639d1de764c478f70f4394fcb1a9f5bffe9011ef0094 | 2013-12-01 00:18:22 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| c174cb0a224a3141ae2c5584e1580e44a4adcf9f6d8acaa7d6ebc84517532f59 | 2013-12-01 09:59:08 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 0f2be50f66e148a67c553a7af5a02b477f17e77bd4ced70a76f5716389faf411 | 2013-12-01 18:26:01 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 55cadfa9851d4b780a8a657efddb28ac3d4d7597e96fac56d4861de4bab077d0 | 2013-12-02 09:55:55 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| ce2da1b828ead9bdca8def3355f2207437788c898d9ed2328ea099daed0e614a | 2013-12-02 15:41:55 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| c1d8b2a29d8420e12400b68cf904a025ab83bc615151b8b980e54b91bd81ab23 | 2013-12-03 10:47:02 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 22ca9e9f39c151cd99e91482a7c05b92229d6af64ea6bcf9e089ae6da2edd6ed | 2013-12-03 19:37:24 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| deed17a5fba540f8bdc46e4d6bf2668fbdf30ce4c1d89cf2ce72fea74d66e928 | 2013-12-04 12:51:54 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 61195d5ceaa70075740321512c991be64bd242444ebbd713a24bce9fea9dfa52 | 2013-12-04 21:30:50 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| c0ae5f6230284d5c042dd89c390e80552d93bd292b3f64d428283974d3837ebc | 2013-12-05 05:58:23 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 11638374fce29030c2eccdfe6b5431e995eff1bb247f4c71296a1ad5f255cd84 | 2013-12-05 21:23:11 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 34d27fbe2b20c2ed9558b11362a8e08c79780a5bfc93d8bfcbf6819f36405464 | 2013-12-06 09:19:02 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 3bb68577a060985e1a7c9b654d6ce52e50d9a1492d55c9eae723c8952311ee5e | 2013-12-06 17:27:51 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 5cc309021e9d7cbb1d51eafda7e00557c3e180769891a3df45a998a471830f3e | 2013-12-07 01:42:49 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| 068b0a6a16be6c97886972f10e734d8d1d10e805be50a106a684aa0853c8d04c | 2013-12-07 09:16:07 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| d432f4f2e7ae83c03d61813b2f9a39694a64e714637b5e605f0c5744f0657ca8 | 2013-12-07 12:22:37 | False | historia previa insuficiente; característica indispensable faltante | — | — | — | — | — | — |  | no_evaluable | — | — | — |
| f9dfa5ed70fab3e624d30bd6d8818e91c3ec12737b606c49c0d1b231220da8d2 | 2013-12-07 20:50:55 | True |  | 7.605273 | 0.748886 | 99.484359 | 99.518735 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 3.348746 | 4.051542 | 0.204985 |
| 2506fb58752f15d45ef0070d4a8fd1db9f3d2e020dfb0f6695dbc11932f1bd45 | 2013-12-08 05:18:17 | True |  | 15.942031 | 0.76825 | 99.553111 | 99.553111 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 6.224109 | 9.477633 | 0.24029 |
| 3d2be087e5174b2c2e111594de3cac1915ede2fb8683e43b942333e7c6ea4aa9 | 2013-12-09 19:08:42 | True |  | 70.20949 | 0.82658 | 99.896872 | 99.656239 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 16.930808 | 52.953759 | 0.324923 |
| 7f093a4a06706aa1ca3810383d50f285e35f757143be5106b9bd20256df68dbb | 2013-12-10 10:16:50 | True |  | 79.797599 | 0.844385 | 99.965624 | 99.793744 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 19.532233 | 59.919873 | 0.345494 |
| eda4bf83d8b9463cf84cc1785f4afb968108ad02d3d265ef652b45877c387152 | 2013-12-10 18:59:13 | True |  | 80.463332 | 0.84696 | 100 | 99.862496 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 20.156018 | 59.951659 | 0.355655 |
| d4124650f46f0e8ad2b23a17a30412cfc0b6fa3943ea63aceccdfb11b0727881 | 2013-12-11 10:04:25 | True |  | 72.562299 | 0.851269 | 99.931248 | 99.965624 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 22.295605 | 49.895559 | 0.371135 |
| 19b481fda64bb018e7f843e16cf438861e427d5a4f7d4c1e5980990a956c4777 | 2013-12-11 18:33:03 | True |  | 70.008122 | 0.851269 | 99.862496 | 99.965624 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 21.398444 | 48.230792 | 0.378885 |
| eb7e19b6ddb14aef7dbfe094167988b16b323acaa0e98992e52557ea97abde15 | 2013-12-13 19:06:49 | True |  | 56.98057 | 0.857048 | 99.82812 | 100 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 24.584558 | 31.981555 | 0.414457 |
| 40e3d1d5fce1ed0116ef99b268a476c3b012e964220fc9bad3743182716858e7 | 2013-12-14 12:04:46 | True |  | 48.237829 | 0.840964 | 99.793744 | 99.759367 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 21.713095 | 26.10033 | 0.424403 |
| f93685a218a8d39d7afd94fab3b085e4ddbea32639f7a188b752735c43709e03 | 2013-12-14 18:08:30 | True |  | 46.33377 | 0.848394 | 99.759367 | 99.896872 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 19.91391 | 25.992129 | 0.42773 |
| 2873c6b6bd765b858a15f39b65f8fabdf0c12b3d6cc64ad70bfc6c01738be476 | 2013-12-15 15:45:09 | True |  | 37.631547 | 0.840111 | 99.724991 | 99.724991 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 19.873226 | 17.319558 | 0.438763 |
| 8a19a1ebd6582547bb7ff7ad2f0a06551f1494c907974cdd1e3469e4af1d2ed4 | 2013-12-16 12:45:46 | True |  | 35.580459 | 0.845243 | 99.690615 | 99.82812 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 19.548643 | 15.58338 | 0.448436 |
| cff171c9161c2972e397796f4d10eb81c6a39b0ebdd8a6565af4a38d08ac9723 | 2013-12-16 18:51:38 | True |  | 33.92216 | 0.837557 | 99.656239 | 99.690615 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 18.641759 | 14.829324 | 0.451077 |
| 6ac66e50bde9832f4d98880b2ffb0bb0d46549022d7f3713288bee5bc695cb69 | 2013-12-17 12:08:47 | True |  | 28.65204 | 0.821006 | 99.621863 | 99.621863 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 17.858253 | 10.335582 | 0.458204 |
| 0c9fc772e811d825f2785b3a007f752f735beb0a0398858861dd01f2bc562103 | 2013-12-17 18:35:24 | True |  | 22.459618 | 0.803605 | 99.587487 | 99.587487 | True | True | ep_378ba9e255f13442c33d4029 | candidato_revision | 15.208795 | 6.790087 | 0.460736 |

## Revisión pendiente

Este prisma no puede considerarse evidencia de falla. Puede representar un comportamiento particular del prisma, una diferencia de escala, un problema de datos o una condición que requiere revisión del especialista. Deben verificarse referencia, integridad de mediciones, ubicación, mantenimiento e historia local. No se elimina ni se utiliza para ajustar parámetros. Su episodio está **censurado al final de las observaciones del propio prisma**; ausencia posterior de mediciones no implica finalización física ni estabilidad.

> Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.
