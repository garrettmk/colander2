import React from "react";
import PropTypes from "prop-types";

import { Segment, Image, Loader, Message } from "semantic-ui-react";

import { DocumentContext } from "../Contexts";
import { defaultImages } from "../style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const headerImgOpts = {
    centered: true,
    rounded: true,
    style: {
        display: 'block'
    }
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ObjectImage (props) {
    let { as, size, ...containerProps } = props;

    if (!as) {
        as = Segment;
        containerProps = containerProps || {
            raised: true,
            textAlign: 'center'
        };
    }

    return (
        <DocumentContext.Consumer>
            { ({ loading, preview }) => {
                let children;

                if (loading)
                    children = <Loader active={true}/>;
                else if (!preview)
                    children = <Message error>No data :(</Message>;
                else
                    children = <Image
                        src={preview.image || defaultImages[preview.type].light}
                        href={preview.url}
                        size={size}
                        {...headerImgOpts}
                    />;

                return React.createElement(as, containerProps, children)
            }}
        </DocumentContext.Consumer>
    )
}


ObjectImage.propTypes = {
    as: PropTypes.string,
    size: PropTypes.oneOf(['mini', 'tiny', 'small', 'medium', 'large', 'big', 'huge', 'massive']),
};


ObjectImage.defaultProps = {
    size: 'medium'
};
