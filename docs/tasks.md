typeの推定ミス
  type: gimick
  name: RBS SuiminSystem 2 - メニュー操作なしで寝返り / OVRで高さ調整【ModularAvatar対応】 - らずべりー工房(はるる早苗)

  type: Texture
  name: 「セレスティア対応」ぬるてか水滴ボディテクスチャ～Sweat Texture～＊2023/06/09 Update!＊ - Atelier Astra
    - BOOTH
  type: Goods
  name: '【3Dモデル】のらなべやカフェセット - #のらなべや - BOOTH'
  shop_name: '#のらなべや'
  - あるべきtype推定ロジックについて考える必要がある。

current_priceの推定ミス
- item_id: 4276444
  type: avatar
  name: オリジナル3dモデル 「かなえ」 Kanae 카나에 - cherry neru - BOOTH
  shop_name: cherry neru
  current_price: 990
- ほかにも多数。
- Boothから取得すれば正しい。


image_urlの処理漏れ
- 画像URLから「/c/{W}x{H}/」を削除して“基のパス”に戻す処理や、`data-original` 等の別属性を探す処理が未実装。
- docs/pximg.md

type:avatarのtargets[code,name]設定漏れ
- SUN,　INABA, 椎名, 狐雨, 猫メイドがアバターだと認識されていない。


dashboard機能追加 : Costumeの対応アバターごとの集計