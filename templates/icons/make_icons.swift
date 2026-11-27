import AppKit
// usage: swift make_icons.swift <out_dir> <hexgray> name=symbol[@weight] ...
// weight: regular (default) or medium. SF Symbols snap to fixed weights, so the 1px tag icons
// (The latest, Wilson Nov 27, 2026) pick per icon whichever weight draws closest to a 1px line at 18px:
//   swift make_icons.swift . 424245 tag-business=briefcase tag-tech=apple.terminal \
//     tag-world=globe.americas tag-pop=popcorn@medium tag-sports=sportscourt@medium
let args = CommandLine.arguments
let out = args[1]
let hex = Int(args[2], radix: 16)!
let color = NSColor(srgbRed: CGFloat((hex>>16)&255)/255, green: CGFloat((hex>>8)&255)/255, blue: CGFloat(hex&255)/255, alpha: 1)
let weights: [String: NSFont.Weight] = ["light": .light, "regular": .regular, "medium": .medium]
for pair in args.dropFirst(3) {
  var p = pair.split(separator: "=").map(String.init)
  let sw = p[1].split(separator: "@").map(String.init)
  p[1] = sw[0]
  let weight = sw.count > 1 ? weights[sw[1]]! : .regular
  let cfg = NSImage.SymbolConfiguration(pointSize: 44, weight: weight)
    .applying(NSImage.SymbolConfiguration(paletteColors: [color]))
  guard let img = NSImage(systemSymbolName: p[1], accessibilityDescription: nil)?.withSymbolConfiguration(cfg) else { print("missing", p[1]); continue }
  let S = 60
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: S, pixelsHigh: S, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.saveGraphicsState()
  NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
  let sz = img.size; let k = min(54/sz.width, 54/sz.height)
  let w = sz.width*k, h = sz.height*k
  img.draw(in: NSRect(x: (CGFloat(S)-w)/2, y: (CGFloat(S)-h)/2, width: w, height: h))
  NSGraphicsContext.restoreGraphicsState()
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(out)/\(p[0]).png"))
  print("ok", p[0], Int(sz.width), Int(sz.height))
}
