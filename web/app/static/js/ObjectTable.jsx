import React from "react";
import { Link } from "react-router-dom";


export default function ObjectList (props) {
    let names = [];
    let attrs = [];

    for (let field in props.fields) {
        names.push(field);
        attrs.push(props.fields[field])
    }

    let linkPrefix = props.linkPrefix;
    let linkOnAttr = props.linkOnAttr;

    return (
        <div className={"outlined"}>
            <h3>{props.title} {props.loading ? '' : '(' + props.total + ')'}</h3>
            {props.loading
                ? 'Loading...'
                : <div>
                    <div style={{display: 'flex'}}>
                        <button onClick={props.onPrevPage ? props.onPrevPage : () => {}}>&lt;</button>
                        <span>Page {props.page} of {props.pages}</span>
                        <button onClick={props.onNextPage ? props.onNextPage : () => {}}>&gt;</button>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                {names.map(n => (
                                    <th key={n}>{n}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                        {props.objects.map(obj => {
                            return (
                                <tr key={obj.id}>
                                    {attrs.map(attr => {
                                        return (
                                            <td key={attr}>
                                                {attr === linkOnAttr
                                                    ? <Link to={linkPrefix + obj.id}>{obj[attr]}</Link>
                                                    : obj[attr]
                                                }
                                            </td>
                                        )
                                    })}
                                </tr>
                            )
                        })}
                        </tbody>
                    </table>
                </div>
            }
        </div>
    )
}