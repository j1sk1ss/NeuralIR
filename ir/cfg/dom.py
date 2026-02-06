from ir.cfg.cfg import CFGBlock, CFGFunction

def complete_successors(funcs: list[CFGFunction]) -> None:
    for func in funcs:
        for block in func.blocks:
            if block.jmp:
                block.succ.add(block.jmp.id)
                block.jmp.pred.add(block.id)
            if block.lin:
                block.succ.add(block.lin.id)
                block.lin.pred.add(block.id)
                
def compute_function_dom(f: CFGFunction) -> None:
    blocks = f.blocks
    if not blocks:
        return

    by_id = {b.id: b for b in blocks}
    all_ids = {b.id for b in blocks}
    entry_id = blocks[0].id

    for b in blocks:
        b.dom.clear()
        if b.id == entry_id:
            b.dom.add(entry_id)
        else:
            b.dom |= all_ids

    changed = True
    while changed:
        changed = False

        for b in blocks:
            if b.id == entry_id:
                continue

            preds = [pid for pid in b.pred if pid in by_id]
            if not preds:
                nd: set[int] = set()
            else:
                nd = set(by_id[preds[0]].dom)
                for pid in preds[1:]:
                    nd &= by_id[pid].dom

            nd.add(b.id)

            if nd != b.dom:
                b.dom = nd
                changed = True
                
def compute_strict_dom(f: CFGFunction) -> None:
    if not f.blocks:
        return

    by_id = {b.id: b for b in f.blocks}
    entry_id = f.blocks[0].id

    by_id[entry_id].sdom = None

    for b in f.blocks:
        if b.id == entry_id:
            continue

        candidates = b.dom - { b.id }
        idom = None

        for d in candidates:
            dominated_by_other = False
            for other in candidates:
                if other == d:
                    continue
                
                if d in by_id[other].dom:
                    dominated_by_other = True
                    break

            if not dominated_by_other:
                idom = by_id[d]
                break

        b.sdom = idom
